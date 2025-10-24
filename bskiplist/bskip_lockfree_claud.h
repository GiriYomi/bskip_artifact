/*
 * ============================================================================
 *
 *       Filename:  bskip.h
 *
 *         Author:  Helen Xu, hjxu@lbl.gov
 *   Organization:  Lawrence Berkeley Laboratory
 *
 * ============================================================================
 */
// EVOLVE-BLOCK-START
#ifndef _BSKIP_H_
#define _BSKIP_H_
#include <algorithm>
#include <cmath>
#include <iostream>
#include <limits>
#include <random>
#include <stack>
#include <string.h>
#include <utility>
#include <vector>
#include <cassert>
#include <atomic>
#include <thread>
#include <chrono>
#include "tbassert.h"
#include <ParallelTools/Lock.hpp>
#include <ParallelTools/parallel.h>
#include <ParallelTools/reducer.h>
#include "StructOfArrays/SizedInt.hpp"
#include "StructOfArrays/aos.hpp"
#include "StructOfArrays/soa.hpp"
#include "tools.h"

// TODO: replace with SOA for vals
#define BINARY_SEARCH 0

// Epoch-based memory reclamation
class EpochManager {
private:
    static constexpr int MAX_THREADS = 128;
    static constexpr int EPOCH_FREQ = 100;
    static constexpr int RETIRE_THRESHOLD = 1000;
    
    struct ThreadState {
        std::atomic<uint64_t> local_epoch{0};
        std::vector<std::pair<uint64_t, void*>> retired_list;
        int op_count = 0;
        char padding[64]; // cache line padding
    };
    
    std::atomic<uint64_t> global_epoch{0};
    ThreadState thread_states[MAX_THREADS];
    
    static thread_local int thread_id;
    static std::atomic<int> thread_counter;
    
    int get_thread_id() {
        if (thread_id == -1) {
            thread_id = thread_counter.fetch_add(1);
        }
        return thread_id;
    }
    
public:
    void enter_epoch() {
        int tid = get_thread_id();
        thread_states[tid].local_epoch.store(global_epoch.load(std::memory_order_acquire), 
                                            std::memory_order_release);
        if (++thread_states[tid].op_count % EPOCH_FREQ == 0) {
            try_advance_epoch();
        }
    }
    
    void exit_epoch() {
        int tid = get_thread_id();
        thread_states[tid].local_epoch.store(UINT64_MAX, std::memory_order_release);
    }
    
    void retire(void* ptr) {
        int tid = get_thread_id();
        uint64_t epoch = global_epoch.load(std::memory_order_acquire);
        thread_states[tid].retired_list.push_back({epoch, ptr});
        
        if (thread_states[tid].retired_list.size() > RETIRE_THRESHOLD) {
            collect_garbage();
        }
    }
    
    void try_advance_epoch() {
        uint64_t curr_epoch = global_epoch.load(std::memory_order_acquire);
        uint64_t min_epoch = curr_epoch;
        
        for (int i = 0; i < MAX_THREADS; i++) {
            uint64_t local = thread_states[i].local_epoch.load(std::memory_order_acquire);
            if (local != UINT64_MAX && local < min_epoch) {
                min_epoch = local;
            }
        }
        
        if (min_epoch == curr_epoch) {
            global_epoch.compare_exchange_weak(curr_epoch, curr_epoch + 1);
        }
    }
    
    void collect_garbage() {
        int tid = get_thread_id();
        uint64_t safe_epoch = UINT64_MAX;
        
        for (int i = 0; i < MAX_THREADS; i++) {
            uint64_t local = thread_states[i].local_epoch.load(std::memory_order_acquire);
            if (local != UINT64_MAX && local < safe_epoch) {
                safe_epoch = local;
            }
        }
        
        auto& retired = thread_states[tid].retired_list;
        auto new_end = std::remove_if(retired.begin(), retired.end(),
            [safe_epoch](const auto& item) {
                if (item.first < safe_epoch) {
                    // Safe to delete
                    operator delete(item.second);
                    return true;
                }
                return false;
            });
        retired.erase(new_end, retired.end());
    }
};

thread_local int EpochManager::thread_id = -1;
std::atomic<int> EpochManager::thread_counter{0};

static EpochManager epoch_manager;

template <typename traits>
class BSkipNode;

template <bool is_concurrent, size_t B, size_t promotion_prob, class T,
          typename... Ts>
class BSkip_traits
{
public:
    static constexpr uint64_t MAX_KEYS = B;
    using key_type = T;
    static constexpr bool binary = sizeof...(Ts) == 0;
    static constexpr bool concurrent = is_concurrent;
    static constexpr size_t p = promotion_prob;
    using element_type =
        typename std::conditional<binary, std::tuple<key_type>,
                                  std::tuple<key_type, Ts...>>::type;
    using value_type =
        typename std::conditional<binary, std::tuple<>, std::tuple<Ts...>>::type;
    template <int I>
    using NthType = typename std::tuple_element<I, value_type>::type;
    static constexpr int num_types = sizeof...(Ts);
    using SOA_leaf_type = typename std::conditional<binary, AOS<key_type>,
                                                    SOA<key_type, Ts...>>::type;
    static key_type get_key(element_type e) { return std::get<0>(e); }
};

template <typename T = uint64_t>
using bskip_set_settings = BSkip_traits<true, 1024, 32, T>;
template <typename T = uint64_t>
using bskip_map_settings = BSkip_traits<true, 1024, 32, T, T>;

// Versioned pointer to prevent ABA and encode state
template <typename T>
class VersionedPointer {
private:
    // Use 48 bits for pointer, 16 bits for version
    static constexpr uintptr_t PTR_MASK = 0x0000FFFFFFFFFFFF;
    static constexpr uintptr_t VERSION_MASK = 0xFFFF000000000000;
    static constexpr int VERSION_SHIFT = 48;
    
    std::atomic<uintptr_t> data{0};
    
public:
    VersionedPointer() = default;
    VersionedPointer(T* ptr, uint16_t version = 0) {
        data.store(pack(ptr, version), std::memory_order_release);
    }
    
    static uintptr_t pack(T* ptr, uint16_t version) {
        uintptr_t p = reinterpret_cast<uintptr_t>(ptr);
        return (p & PTR_MASK) | (static_cast<uintptr_t>(version) << VERSION_SHIFT);
    }
    
    T* get_ptr() const {
        uintptr_t val = data.load(std::memory_order_acquire);
        return reinterpret_cast<T*>(val & PTR_MASK);
    }
    
    uint16_t get_version() const {
        uintptr_t val = data.load(std::memory_order_acquire);
        return (val >> VERSION_SHIFT) & 0xFFFF;
    }
    
    std::pair<T*, uint16_t> load() const {
        uintptr_t val = data.load(std::memory_order_acquire);
        return {reinterpret_cast<T*>(val & PTR_MASK), 
                (val >> VERSION_SHIFT) & 0xFFFF};
    }
    
    bool compare_exchange_weak(T*& expected_ptr, uint16_t& expected_version,
                               T* new_ptr, uint16_t new_version) {
        uintptr_t expected = pack(expected_ptr, expected_version);
        uintptr_t desired = pack(new_ptr, new_version);
        
        if (data.compare_exchange_weak(expected, desired,
                                       std::memory_order_release,
                                       std::memory_order_acquire)) {
            return true;
        }
        expected_ptr = reinterpret_cast<T*>(expected & PTR_MASK);
        expected_version = (expected >> VERSION_SHIFT) & 0xFFFF;
        return false;
    }
    
    void store(T* ptr, uint16_t version) {
        data.store(pack(ptr, version), std::memory_order_release);
    }
};

// Base class for B-skip nodes
template <typename traits>
class BSkipNode
{
public:
    std::atomic<uint32_t> num_elts{0};
    uint32_t level;
    VersionedPointer<BSkipNode<traits>> next;
    std::atomic<typename traits::key_type> next_header{std::numeric_limits<typename traits::key_type>::max()};
    std::atomic<uint64_t> version{0}; // Version for validation
    
    BSkipNode() {
        num_elts = 0;
        next_header = std::numeric_limits<typename traits::key_type>::max();
    }
    
    virtual ~BSkipNode() {}
    
    bool is_leafnode() const { return (level == 0); }
    
    virtual typename traits::key_type get_header() = 0;
    virtual uint32_t find_key(typename traits::key_type k) = 0;
    virtual std::pair<uint32_t, bool> find_key_and_check(typename traits::key_type k) = 0;
    virtual typename traits::key_type get_key_at_rank(uint32_t rank) = 0;
    virtual void insert_key_at_rank(uint32_t rank, typename traits::key_type key) = 0;
    virtual int split_keys(BSkipNode<traits> *dest, uint32_t starting_rank,
                           uint32_t dest_rank = 1) = 0;
    virtual void print_keys() = 0;
};

class Empty
{
};

// Immutable leaf node for copy-on-write
template <typename traits>
class BSkipNodeLeaf : public BSkipNode<traits>
{
public:
    using K = typename traits::key_type;
    using V = typename traits::value_type;
    using elt_type = typename traits::element_type;
    static constexpr typename traits::key_type NULL_VAL = {};
    static constexpr size_t max_element_size = sizeof(K);
    using SOA_type = typename traits::SOA_leaf_type;
    static constexpr uint64_t max_size = traits::MAX_KEYS;
    
    std::array<uint8_t, SOA_type::get_size_static(max_size)> array = {0};
    
    inline K get_key_array(uint32_t index) const
    {
        return std::get<0>(
            SOA_type::template get_static<0>(array.data(), max_size, index));
    }
    
    auto blind_read_key(uint32_t index) const
    {
        return std::get<0>(SOA_type::get_static(array.data(), max_size, index));
    }
    
    auto blind_read_val(uint32_t index) const
    {
        if constexpr (!traits::binary) {
            return std::get<1>(SOA_type::get_static(array.data(), max_size, index));
        } else {
            return V{};
        }
    }
    
    void blind_write_array(void *arr, size_t len, uint32_t index,
                           typename traits::element_type e)
    {
        SOA_type::get_static(arr, len, index) = e;
    }
    
    void blind_write(typename traits::element_type e, uint32_t index)
    {
        SOA_type::get_static(array.data(), max_size, index) = e;
    }
    
    auto blind_read(uint32_t index) const
    {
        return SOA_type::get_static(array.data(), max_size, index);
    }
    
    auto blind_read_array(void *arr, size_t size, uint32_t index) const
    {
        return SOA_type::get_static(arr, size, index);
    }
    
    auto blind_read_key_array(void *arr, size_t size, uint32_t index) const
    {
        return std::get<0>(SOA_type::get_static(arr, size, index));
    }
    
    size_t count_up_elts() const
    {
        size_t result = 0;
        for (size_t i = 0; i < max_size; i++)
        {
            result += (blind_read_key(i) != NULL_VAL);
        }
        return result;
    }
    
    inline K get_header()
    {
        return blind_read_key(0);
    }
    
    uint64_t sum_keys()
    {
        uint64_t result = 0;
        uint32_t n = BSkipNode<traits>::num_elts.load(std::memory_order_acquire);
        for (uint32_t i = 0; i < n; i++)
        {
            result += blind_read_key(i);
        }
        return result;
    }
    
    uint64_t sum_vals()
    {
        uint64_t result = 0;
        uint32_t n = BSkipNode<traits>::num_elts.load(std::memory_order_acquire);
        for (uint32_t i = 0; i < n; i++)
        {
            if constexpr (!traits::binary) {
                result += blind_read_val(i);
            }
        }
        return result;
    }
    
    void print_keys()
    {
        uint32_t n = BSkipNode<traits>::num_elts.load(std::memory_order_acquire);
        printf("\tlevel = %u, num keys = %u\n", BSkipNode<traits>::level, n);
        for (uint32_t i = 0; i < n; i++)
        {
            printf("\t\tkey[%d] = %lu\n", i, (unsigned long)blind_read_key(i));
        }
        printf("\n");
    }
    
    uint32_t find_key(K k)
    {
#if BINARY_SEARCH
        return find_index_binary(k);
#else
        return find_index_linear(k);
#endif
    }
    
    std::pair<uint32_t, bool> find_key_and_check(K k)
    {
#if BINARY_SEARCH
        auto index = find_index_binary(k);
        return {index, (blind_read_key(index) == k)};
#else
        auto index = find_index_linear(k);
        return {index, (blind_read_key(index) == k)};
#endif
    }
    
    void insert_elt_at_rank(uint32_t rank, typename traits::element_type elt)
    {
        uint32_t n = BSkipNode<traits>::num_elts.load(std::memory_order_acquire);
        assert(n + 1 <= max_size);
        for (size_t j = n; j > rank; j--)
        {
            SOA_type::get_static(array.data(), max_size, j) =
                SOA_type::get_static(array.data(), max_size, j - 1);
        }
        blind_write(elt, rank);
    }
    
    inline K get_key_at_rank(uint32_t rank)
    {
        return blind_read_key(rank);
    }
    
    inline V get_value_at_rank(uint32_t rank)
    {
        if constexpr (!traits::binary) {
            return blind_read_val(rank);
        } else {
            return V{};
        }
    }
    
    void insert_key_at_rank(uint32_t rank, typename traits::key_type key)
    {
        (void)rank;
        (void)key;
        assert(false);
    }
    
    inline void set_elt_at_rank(uint32_t rank, typename traits::element_type elt)
    {
        assert(rank < BSkipNode<traits>::num_elts.load(std::memory_order_acquire));
        blind_write(elt, rank);
    }
    
    int split_keys(BSkipNode<traits> *dest, uint32_t starting_rank,
                   uint32_t dest_rank = 1)
    {
        uint32_t n = BSkipNode<traits>::num_elts.load(std::memory_order_acquire);
        uint32_t num_elts_to_move = n - starting_rank;
        assert(starting_rank <= n);
        assert(num_elts_to_move <= n);
        assert(num_elts_to_move < traits::MAX_KEYS);
        
        for (uint32_t j = 0; j < num_elts_to_move; j++)
        {
            ((BSkipNodeLeaf<traits> *)dest)
                ->blind_write(blind_read(starting_rank + j), dest_rank + j);
        }
        
        BSkipNode<traits>::num_elts.store(starting_rank, std::memory_order_release);
        dest->num_elts.fetch_add(num_elts_to_move, std::memory_order_release);
        return num_elts_to_move;
    }
    
    // Create a new leaf with an element inserted
    BSkipNodeLeaf<traits>* create_with_insert(uint32_t rank, typename traits::element_type elt) {
        auto* new_leaf = new BSkipNodeLeaf<traits>();
        uint32_t n = BSkipNode<traits>::num_elts.load(std::memory_order_acquire);
        
        // Copy elements before insertion point
        for (uint32_t i = 0; i < rank; i++) {
            new_leaf->blind_write(blind_read(i), i);
        }
        
        // Insert new element
        new_leaf->blind_write(elt, rank);
        
        // Copy elements after insertion point
        for (uint32_t i = rank; i < n; i++) {
            new_leaf->blind_write(blind_read(i), i + 1);
        }
        
        new_leaf->num_elts.store(n + 1, std::memory_order_release);
        new_leaf->level = 0;
        new_leaf->next.store(BSkipNode<traits>::next.get_ptr(), 0);
        new_leaf->next_header.store(BSkipNode<traits>::next_header.load(std::memory_order_acquire));
        
        return new_leaf;
    }
    
    // Create a new leaf with an element updated
    BSkipNodeLeaf<traits>* create_with_update(uint32_t rank, typename traits::element_type elt) {
        auto* new_leaf = new BSkipNodeLeaf<traits>();
        uint32_t n = BSkipNode<traits>::num_elts.load(std::memory_order_acquire);
        
        // Copy all elements, replacing at rank
        for (uint32_t i = 0; i < n; i++) {
            if (i == rank) {
                new_leaf->blind_write(elt, i);
            } else {
                new_leaf->blind_write(blind_read(i), i);
            }
        }
        
        new_leaf->num_elts.store(n, std::memory_order_release);
        new_leaf->level = 0;
        new_leaf->next.store(BSkipNode<traits>::next.get_ptr(), 0);
        new_leaf->next_header.store(BSkipNode<traits>::next_header.load(std::memory_order_acquire));
        
        return new_leaf;
    }
    
private:
    uint32_t find_index_linear(K k)
    {
        uint32_t i;
        uint32_t n = BSkipNode<traits>::num_elts.load(std::memory_order_acquire);
        assert(n > 0);
        for (i = 0; i < n; i++)
        {
            if (blind_read_key(i) < k)
                continue;
            else if (k == blind_read_key(i))
            {
                return i;
            }
            else
                break;
        }
        return i - 1;
    }
    
    uint32_t find_index_binary(K k)
    {
        uint32_t n = BSkipNode<traits>::num_elts.load(std::memory_order_acquire);
        uint32_t left = 0;
        uint32_t right = n - 1;
        while (left <= right)
        {
            int mid = left + (right - left) / 2;
            if (blind_read_key(mid) == k)
            {
                left = mid;
                break;
            }
            else if (blind_read_key(mid) < k)
            {
                left = mid + 1;
            }
            else
            {
                if (mid == 0)
                {
                    break;
                }
                right = mid - 1;
            }
        }
        if (left == n || blind_read_key(left) > k)
        {
            assert(left > 0);
            left--;
        }
        return left;
    }
};

// Internal node
template <typename traits>
class BSkipNodeInternal : public BSkipNode<traits>
{
    using K = typename traits::key_type;
    
public:
    K keys[traits::MAX_KEYS];
    VersionedPointer<BSkipNode<traits>> children[traits::MAX_KEYS];
    
    BSkipNodeInternal() {}
    
    inline K get_header() { 
        return keys[0]; 
    }
    
    void set_key_at_rank(uint32_t rank, K key)
    {
        keys[rank] = key;
    }
    
    void insert_child_at_rank(uint32_t rank, BSkipNode<traits> *elt, bool flag = true)
    {
        uint32_t n = this->num_elts.load(std::memory_order_acquire);
        assert(n <= traits::MAX_KEYS);
        
        if (flag)
        {
            memmove(children + rank + 1, children + rank,
                    (n - rank - 1) * sizeof(VersionedPointer<BSkipNode<traits>>));
        }
        else
        {
            memmove(children + rank + 1, children + rank,
                    (n - rank) * sizeof(VersionedPointer<BSkipNode<traits>>));
        }
        children[rank].store(elt, 0);
    }
    
    BSkipNode<traits> *get_child_at_rank(uint32_t rank)
    {
        return children[rank].get_ptr();
    }
    
    void set_child_at_rank(uint32_t rank, BSkipNode<traits> *elt)
    {
        children[rank].store(elt, 0);
    }
    
    void move_children(BSkipNodeInternal<traits> *dest, uint32_t starting_rank,
                       uint32_t num_elts_to_move, uint32_t dest_rank = 1)
    {
        assert(num_elts_to_move < traits::MAX_KEYS);
        memmove(dest->children + dest_rank, children + starting_rank,
                num_elts_to_move * sizeof(VersionedPointer<BSkipNode<traits>>));
    }
    
    uint32_t find_key(typename traits::key_type k)
    {
        uint32_t i;
        uint32_t n = BSkipNode<traits>::num_elts.load(std::memory_order_acquire);
        assert(n > 0);
        
        for (i = 0; i < n; i++)
        {
            if (keys[i] > k)
                break;
        }
        if (i == 0) {
            return 0;
        }
        return i - 1;
    }
    
    std::pair<uint32_t, bool> find_key_and_check(typename traits::key_type k)
    {
        uint32_t i;
        uint32_t n = BSkipNode<traits>::num_elts.load(std::memory_order_acquire);
        assert(n > 0);
        
        for (i = 0; i < n; i++)
        {
            if (keys[i] > k)
                break;
        }
        if (i == 0) {
            return {0, keys[i] == k};
        }
        return {i - 1, keys[i-1] == k};
    }
    
    typename traits::key_type get_key_at_rank(uint32_t rank)
    {
        return keys[rank];
    }
    
    void insert_key_at_rank(uint32_t rank, typename traits::key_type key)
    {
        assert(this->level > 0);
        uint32_t n = this->num_elts.load(std::memory_order_acquire);
        assert(n + 1 <= traits::MAX_KEYS);
        
        memmove(keys + rank + 1, keys + rank,
                (n - rank) * sizeof(K));
        keys[rank] = key;
    }
    
    int split_keys(BSkipNode<traits> *dest, uint32_t starting_rank,
                   uint32_t dest_rank = 1)
    {
        uint32_t n = this->num_elts.load(std::memory_order_acquire);
        uint32_t num_elts_to_move = n - starting_rank;
        assert(starting_rank <= n);
        assert(num_elts_to_move <= n);
        assert(num_elts_to_move < traits::MAX_KEYS);
        
        memmove(((BSkipNodeInternal<traits> *)(dest))->keys + dest_rank,
                keys + starting_rank, num_elts_to_move * sizeof(K));
        this->num_elts.store(starting_rank, std::memory_order_release);
        dest->num_elts.fetch_add(num_elts_to_move, std::memory_order_release);
        return num_elts_to_move;
    }
    
    void print_keys()
    {
        uint32_t n = BSkipNode<traits>::num_elts.load(std::memory_order_acquire);
        printf("\tlevel = %u, num keys = %u\n", BSkipNode<traits>::level, n);
        for (uint32_t i = 0; i < n; i++)
        {
            printf("\t\tkey[%d] = %lu\n", i, (unsigned long)keys[i]);
        }
        printf("\n");
    }
};

// Lock-free B-skip list
template <typename traits>
class BSkip
{
    using K = typename traits::key_type;
    static constexpr uint32_t MAX_HEIGHT = 5;
    
public:
#if STATS
    mutable std::atomic<int> query_counter = 0;
    mutable std::atomic<int> steps_counter = 0;
    mutable ThreadSafeVector<int> steps_vector;
    mutable std::atomic<int> write_lock_counter = 0;
    mutable std::atomic<int> read_lock_counter = 0;
    mutable std::atomic<int> range_length_counter = 0;
    mutable std::atomic<int> range_length_node_counter = 0;
#endif
    
    static constexpr double promotion_probability = (double)(1.0) / (double)traits::p;
    bool has_zero = false;
    BSkipNode<traits> *headers[MAX_HEIGHT];
    
#if ENABLE_TRACE_TIMER
    ParallelTools::Reducer_sum<uint64_t> read_lock_count;
    ParallelTools::Reducer_sum<uint64_t> write_lock_count;
    ParallelTools::Reducer_sum<uint64_t> leaf_lock_count;
    
    void get_lock_counts()
    {
        printf("read lock count = %lu, write_lock_count = %lu, leaf lock count = "
               "%lu\n",
               read_lock_count.get(), write_lock_count.get(),
               leaf_lock_count.get());
    }
    void reset_lock_counts()
    {
        read_lock_count -= read_lock_count.get();
        write_lock_count -= write_lock_count.get();
        leaf_lock_count -= leaf_lock_count.get();
    }
    uint64_t get_read_lock_count() { return read_lock_count.get(); }
    uint64_t get_write_lock_count() { return write_lock_count.get(); }
    uint64_t get_leaf_lock_count() { return leaf_lock_count.get(); }
    uint64_t insert(typename traits::element_type k);
#else
    bool insert(typename traits::element_type k);
#endif
    
    BSkipNode<traits> *find(typename traits::key_type k) const;
    typename traits::value_type value(typename traits::key_type k) const;
    bool exists(typename traits::key_type k) const;
    
    template <class F>
    void map_range_length(typename traits::key_type start, uint64_t length, F f) const;
    
    template <class F>
    void map_range(typename traits::key_type min, typename traits::key_type max, F f) const;
    
    uint64_t sum();
    uint64_t sum_vals();
    uint64_t psum();
    void validate_structure();
    void get_size_stats();
    void get_avg_comparisons();
    uint32_t flip_coins(typename traits::key_type k);
    int node_size;
    
    void clear_stats() {
    #if STATS
        query_counter = 0;
        steps_counter = 0;
        write_lock_counter = 0;
        read_lock_counter = 0;
        range_length_counter = 0;
        range_length_node_counter = 0;
    #endif
    }
    
    static_assert(MAX_HEIGHT > 1);
    
    BSkip()
    {
        for (uint32_t i = 0; i < MAX_HEIGHT; i++)
        {
            if (i > 0)
            {
                headers[i] = new BSkipNodeInternal<traits>();
                auto end_sentinel = new BSkipNodeInternal<traits>();
                end_sentinel->level = i;
                end_sentinel->num_elts.store(1, std::memory_order_release);
                end_sentinel->set_key_at_rank(0, std::numeric_limits<K>::max());
                headers[i]->next.store(end_sentinel, 0);
            }
            else
            {
                headers[i] = new BSkipNodeLeaf<traits>();
                auto end_sentinel = new BSkipNodeLeaf<traits>();
                typename traits::element_type sentinel;
                std::get<0>(sentinel) =
                    std::numeric_limits<typename traits::key_type>::max();
                end_sentinel->blind_write(sentinel, 0);
                end_sentinel->level = i;
                end_sentinel->num_elts.store(1, std::memory_order_release);
                headers[i]->next.store(end_sentinel, 0);
            }
        }
        
        for (int i = MAX_HEIGHT - 1; i >= 0; i--)
        {
            headers[i]->num_elts.store(1, std::memory_order_release);
            if (i > 0)
            {
                ((BSkipNodeInternal<traits> *)headers[i])
                    ->set_key_at_rank(0, std::numeric_limits<K>::min());
            }
            else
            {
                typename traits::element_type sentinel;
                std::get<0>(sentinel) =
                    std::numeric_limits<typename traits::key_type>::min();
                ((BSkipNodeLeaf<traits> *)headers[i])->blind_write(sentinel, 0);
            }
            headers[i]->level = i;
            if (i > 0)
            {
                ((BSkipNodeInternal<traits> *)headers[i])
                    ->set_child_at_rank(0, headers[i - 1]);
            }
            if (i == 0)
            {
                break;
            }
        }
    }
    
    ~BSkip()
    {
#if STATS
        int queries = query_counter.load();
        int steps = steps_counter.load();
        printf("average query horizontal steps = %f\n", (double)steps / (double)queries);
        
        int write_locks = write_lock_counter.load();
        printf("write locks aquired = %d\n", write_locks);
        
        int read_locks = read_lock_counter.load();
        printf("read locks aquired = %d\n", read_locks);
        
        int range_length = range_length_counter.load();
        int range_length_nodes = range_length_node_counter.load();
        printf("range length average nodes searched: %f\n", (double)range_length_nodes / (double)range_length);
#endif
        BSkipNodeInternal<traits> *curr_node, *next_node;
        for (uint32_t i = 1; i < MAX_HEIGHT; i++)
        {
            curr_node = ((BSkipNodeInternal<traits> *)headers[i]);
            while (curr_node)
            {
                next_node = (BSkipNodeInternal<traits> *)curr_node->next.get_ptr();
                delete curr_node;
                curr_node = next_node;
            }
        }
        BSkipNodeLeaf<traits> *curr_leaf, *next_leaf;
        curr_leaf = (BSkipNodeLeaf<traits> *)headers[0];
        while (curr_leaf)
        {
            next_leaf = (BSkipNodeLeaf<traits> *)curr_leaf->next.get_ptr();
            delete curr_leaf;
            curr_leaf = next_leaf;
        }
    }
    
    void print_leaves()
    {
        auto n = headers[0];
        while (n)
        {
            n->print_keys();
            n = n->next.get_ptr();
        }
    }
    
private:
    void sum_helper(std::vector<uint64_t> &sums, BSkipNode<traits> *node,
                    int level, typename traits::key_type max);
    
    // Helper structure for tracking parent nodes during traversal
    struct ParentInfo {
        BSkipNode<traits>* node;
        uint32_t rank;
        uint64_t version;
    };
};

// Lock-free insert using copy-on-write for leaves
template <typename traits>
#if ENABLE_TRACE_TIMER
uint64_t BSkip<traits>::insert(typename traits::element_type k)
{
#else
bool BSkip<traits>::insert(typename traits::element_type k)
{
#endif
    typename traits::key_type key = std::get<0>(k);
    
    if (key == 0)
    {
        has_zero = true;
        return true;
    }
    
    epoch_manager.enter_epoch();
    
    uint32_t level_to_promote = flip_coins(key);
    const int MAX_RETRIES = 100;
    
    for (int retry = 0; retry < MAX_RETRIES; retry++) {
        // Track parent nodes and versions for validation
        ParentInfo parents[MAX_HEIGHT];
        BSkipNode<traits>* curr_node = headers[MAX_HEIGHT - 1];
        
        // Phase 1: Find insertion point and collect parent info
        bool valid = true;
        for (int level = MAX_HEIGHT - 1; level >= 0; level--) {
            uint64_t node_version = curr_node->version.load(std::memory_order_acquire);
            
            // Traverse horizontally
            while (true) {
                K next_hdr = curr_node->next_header.load(std::memory_order_acquire);
                if (key < next_hdr) break;
                
                auto next = curr_node->next.get_ptr();
                if (!next) break;
                curr_node = next;
                node_version = curr_node->version.load(std::memory_order_acquire);
            }
            
            // Find position in current node
            auto [rank, found_key] = curr_node->find_key_and_check(key);
            
            if (found_key) {
                // Key already exists - handle update for maps
                if constexpr (!traits::binary) {
                    if (level == 0) {
                        // Copy-on-write update for leaf
                        BSkipNodeLeaf<traits>* leaf = (BSkipNodeLeaf<traits>*)curr_node;
                        BSkipNodeLeaf<traits>* new_leaf = leaf->create_with_update(rank, k);
                        
                        // Try to install new leaf
                        if (level > 0 && parents[level+1].node) {
                            BSkipNodeInternal<traits>* parent = (BSkipNodeInternal<traits>*)parents[level+1].node;
                            auto old_child = parent->children[parents[level+1].rank].get_ptr();
                            uint16_t old_version = parent->children[parents[level+1].rank].get_version();
                            
                            if (parent->children[parents[level+1].rank].compare_exchange_weak(
                                    old_child, old_version, new_leaf, old_version + 1)) {
                                epoch_manager.retire(leaf);
                                epoch_manager.exit_epoch();
                                return true;
                            } else {
                                delete new_leaf;
                            }
                        }
                    }
                }
                epoch_manager.exit_epoch();
                return true;
            }
            
            // Store parent info
            parents[level] = {curr_node, rank, node_version};
            
            // Move down if not at leaf level
            if (level > 0) {
                BSkipNodeInternal<traits>* internal = (BSkipNodeInternal<traits>*)curr_node;
                curr_node = internal->get_child_at_rank(rank);
                if (!curr_node) {
                    valid = false;
                    break;
                }
            }
        }
        
        if (!valid) continue;
        
        // Phase 2: Perform insertion at leaf level
        if (parents[0].node && parents[0].node->level == 0) {
            BSkipNodeLeaf<traits>* leaf = (BSkipNodeLeaf<traits>*)parents[0].node;
            uint32_t insert_rank = parents[0].rank + 1;
            
            // Check if split is needed
            uint32_t num_elts = leaf->num_elts.load(std::memory_order_acquire);
            if (num_elts + 1 > traits::MAX_KEYS) {
                // TODO: Implement split logic
                // For now, just retry
                continue;
            }
            
            // Create new leaf with element inserted
            BSkipNodeLeaf<traits>* new_leaf = leaf->create_with_insert(insert_rank, k);
            
            // Try to install new leaf by updating parent pointer
            bool installed = false;
            
            // Find the parent that points to this leaf
            for (int plevel = 1; plevel < MAX_HEIGHT; plevel++) {
                if (parents[plevel].node && parents[plevel].node->level == plevel) {
                    BSkipNodeInternal<traits>* parent = (BSkipNodeInternal<traits>*)parents[plevel].node;
                    
                    // Find which child pointer points to our leaf
                    for (uint32_t i = 0; i <= parents[plevel].rank; i++) {
                        auto child = parent->children[i].get_ptr();
                        if (child == leaf) {
                            uint16_t old_version = parent->children[i].get_version();
                            if (parent->children[i].compare_exchange_weak(
                                    child, old_version, new_leaf, old_version + 1)) {
                                installed = true;
                                epoch_manager.retire(leaf);
                                break;
                            }
                        }
                    }
                    if (installed) break;
                }
            }
            
            if (installed) {
                epoch_manager.exit_epoch();
                return true;
            } else {
                delete new_leaf;
            }
        }
    }
    
    epoch_manager.exit_epoch();
    return false;
}

// Lock-free value lookup
template <typename traits>
typename traits::value_type BSkip<traits>::value(typename traits::key_type k) const
{
#if STATS
    this->query_counter++;
    int local_step_counter = 0;
#endif
    
    epoch_manager.enter_epoch();
    
    const int MAX_RETRIES = 100;
    
    for (int retry = 0; retry < MAX_RETRIES; retry++) {
        BSkipNode<traits>* curr_node = headers[MAX_HEIGHT - 1];
        uint64_t version = curr_node->version.load(std::memory_order_acquire);
        
        for (int level = MAX_HEIGHT - 1; level >= 0; level--) {
            // Traverse horizontally
            while (true) {
                K next_hdr = curr_node->next_header.load(std::memory_order_acquire);
                if (k < next_hdr) break;
                
                auto next = curr_node->next.get_ptr();
                if (!next) break;
                
                curr_node = next;
                
#if STATS
                this->steps_counter++;
                local_step_counter++;
#endif
                
                // Check version for consistency
                uint64_t new_version = curr_node->version.load(std::memory_order_acquire);
                if (new_version != version) {
                    // Node changed, retry from top
                    goto retry_search;
                }
                version = new_version;
            }
            
            // Find in current node
            auto [rank, found_key] = curr_node->find_key_and_check(k);
            
            if (found_key) {
                // Found the key
                typename traits::value_type result;
                if (level == 0) {
                    BSkipNodeLeaf<traits>* leaf = (BSkipNodeLeaf<traits>*)curr_node;
                    result = leaf->get_value_at_rank(rank);
                    
                    // Validate version didn't change
                    if (curr_node->version.load(std::memory_order_acquire) == version) {
#if STATS
                        this->steps_vector.push_back(local_step_counter);
#endif
                        epoch_manager.exit_epoch();
                        return result;
                    }
                    goto retry_search;
                } else {
                    // Navigate down to leaf
                    BSkipNodeInternal<traits>* internal = (BSkipNodeInternal<traits>*)curr_node;
                    BSkipNode<traits>* child = internal->get_child_at_rank(rank);
                    
                    while (child && child->level > 0) {
                        internal = (BSkipNodeInternal<traits>*)child;
                        child = internal->get_child_at_rank(0);
                    }
                    
                    if (child && child->level == 0) {
                        BSkipNodeLeaf<traits>* leaf = (BSkipNodeLeaf<traits>*)child;
                        result = leaf->get_value_at_rank(0);
#if STATS
                        this->steps_vector.push_back(local_step_counter);
#endif
                        epoch_manager.exit_epoch();
                        return result;
                    }
                }
            }
            
            // Move down a level
            if (level > 0) {
                BSkipNodeInternal<traits>* internal = (BSkipNodeInternal<traits>*)curr_node;
                curr_node = internal->get_child_at_rank(rank);
                if (!curr_node) {
                    goto retry_search;
                }
                version = curr_node->version.load(std::memory_order_acquire);
            }
        }
        
        retry_search:;
    }
    
#if STATS
    this->steps_vector.push_back(local_step_counter);
#endif
    
    epoch_manager.exit_epoch();
    return typename traits::value_type{};
}

// Lock-free exists check
template <typename traits>
bool BSkip<traits>::exists(typename traits::key_type k) const
{
    epoch_manager.enter_epoch();
    
    const int MAX_RETRIES = 100;
    
    for (int retry = 0; retry < MAX_RETRIES; retry++) {
        BSkipNode<traits>* curr_node = headers[MAX_HEIGHT - 1];
        uint64_t version = curr_node->version.load(std::memory_order_acquire);
        
        for (int level = MAX_HEIGHT - 1; level >= 0; level--) {
            // Traverse horizontally
            while (true) {
                K next_hdr = curr_node->next_header.load(std::memory_order_acquire);
                if (k < next_hdr) break;
                
                auto next = curr_node->next.get_ptr();
                if (!next) break;
                
                curr_node = next;
                
                // Check version for consistency
                uint64_t new_version = curr_node->version.load(std::memory_order_acquire);
                if (new_version != version) {
                    // Node changed, retry
                    goto retry_exists;
                }
                version = new_version;
            }
            
            // Find in current node
            auto [rank, found_key] = curr_node->find_key_and_check(k);
            
            if (found_key) {
                // Validate version
                if (curr_node->version.load(std::memory_order_acquire) == version) {
                    epoch_manager.exit_epoch();
                    return true;
                }
                goto retry_exists;
            }
            
            // Move down
            if (level > 0) {
                BSkipNodeInternal<traits>* internal = (BSkipNodeInternal<traits>*)curr_node;
                curr_node = internal->get_child_at_rank(rank);
                if (!curr_node) {
                    goto retry_exists;
                }
                version = curr_node->version.load(std::memory_order_acquire);
            }
        }
        
        retry_exists:;
    }
    
    epoch_manager.exit_epoch();
    return false;
}

// Find helper
template <typename traits>
BSkipNode<traits> *BSkip<traits>::find(typename traits::key_type k) const
{
    epoch_manager.enter_epoch();
    
    const int MAX_RETRIES = 100;
    
    for (int retry = 0; retry < MAX_RETRIES; retry++) {
        BSkipNode<traits>* curr_node = headers[MAX_HEIGHT - 1];
        
        for (int level = MAX_HEIGHT - 1; level >= 0; level--) {
            // Traverse horizontally
            while (curr_node->next_header.load(std::memory_order_acquire) <= k) {
                curr_node = curr_node->next.get_ptr();
                if (!curr_node) {
                    goto retry_find;
                }
            }
            
            auto [rank, found] = curr_node->find_key_and_check(k);
            if (curr_node->get_key_at_rank(rank) == k) {
                epoch_manager.exit_epoch();
                return curr_node;
            }
            
            if (level > 0) {
                BSkipNodeInternal<traits>* internal = (BSkipNodeInternal<traits>*)curr_node;
                curr_node = internal->get_child_at_rank(rank);
                if (!curr_node) {
                    goto retry_find;
                }
            }
        }
        
        retry_find:;
    }
    
    epoch_manager.exit_epoch();
    return nullptr;
}

// Lock-free range query with validation
template <typename traits>
template <class F>
void BSkip<traits>::map_range(typename traits::key_type min, typename traits::key_type max, F f) const
{
    epoch_manager.enter_epoch();
    
    const int MAX_RETRIES = 100;
    
    for (int retry = 0; retry < MAX_RETRIES; retry++) {
        // Find starting position
        BSkipNode<traits>* curr_node = headers[MAX_HEIGHT - 1];
        uint64_t version = curr_node->version.load(std::memory_order_acquire);
        uint32_t current_key_rank = 0;
        bool found = false;
        
        // Navigate to starting position
        for (int level = MAX_HEIGHT - 1; level >= 0; level--) {
            while (curr_node->next_header.load(std::memory_order_acquire) <= min) {
                curr_node = curr_node->next.get_ptr();
                if (!curr_node) goto retry_range;
                
                uint64_t new_version = curr_node->version.load(std::memory_order_acquire);
                if (new_version != version) goto retry_range;
                version = new_version;
            }
            
            auto [rank, found_key] = curr_node->find_key_and_check(min);
            current_key_rank = rank;
            if (found_key) {
                found = true;
                break;
            }
            
            if (level > 0) {
                BSkipNodeInternal<traits>* internal = (BSkipNodeInternal<traits>*)curr_node;
                curr_node = internal->get_child_at_rank(current_key_rank);
                if (!curr_node) goto retry_range;
                version = curr_node->version.load(std::memory_order_acquire);
            }
        }
        
        // Navigate down to leaf
        while (curr_node->level > 0) {
            BSkipNodeInternal<traits>* internal = (BSkipNodeInternal<traits>*)curr_node;
            curr_node = internal->get_child_at_rank(found ? current_key_rank : 0);
            if (!curr_node) goto retry_range;
            version = curr_node->version.load(std::memory_order_acquire);
            if (!found) current_key_rank = curr_node->find_key(min);
        }
        
        // Adjust starting position if min not found
        if (!found) {
            current_key_rank++;
            uint32_t n = curr_node->num_elts.load(std::memory_order_acquire);
            if (current_key_rank == n) {
                curr_node = curr_node->next.get_ptr();
                if (!curr_node) {
                    epoch_manager.exit_epoch();
                    return;
                }
                current_key_rank = 0;
                version = curr_node->version.load(std::memory_order_acquire);
            }
        }
        
        // Traverse and apply function
        BSkipNodeLeaf<traits>* leaf = (BSkipNodeLeaf<traits>*)curr_node;
        while (leaf && leaf->get_key_at_rank(current_key_rank) <= max && 
               leaf->get_key_at_rank(current_key_rank) != std::numeric_limits<K>::max()) {
            
            // Apply function
            f(leaf->get_key_at_rank(current_key_rank), 
              leaf->get_value_at_rank(current_key_rank));
            
            // Check version for consistency
            if (leaf->version.load(std::memory_order_acquire) != version) {
                goto retry_range;
            }
            
            current_key_rank++;
            uint32_t n = leaf->num_elts.load(std::memory_order_acquire);
            if (current_key_rank == n) {
                leaf = (BSkipNodeLeaf<traits>*)leaf->next.get_ptr();
                if (!leaf) break;
                current_key_rank = 0;
                version = leaf->version.load(std::memory_order_acquire);
            }
        }
        
        // Successfully completed range query
        epoch_manager.exit_epoch();
        return;
        
        retry_range:;
    }
    
    epoch_manager.exit_epoch();
}

// Lock-free range query with length
template <typename traits>
template <class F>
void BSkip<traits>::map_range_length(typename traits::key_type start, uint64_t length, F f) const
{
    epoch_manager.enter_epoch();
    
#if STATS
    this->range_length_counter++;
#endif
    
    const int MAX_RETRIES = 100;
    
    for (int retry = 0; retry < MAX_RETRIES; retry++) {
        // Find starting position
        BSkipNode<traits>* curr_node = headers[MAX_HEIGHT - 1];
        uint64_t version = curr_node->version.load(std::memory_order_acquire);
        uint32_t current_key_rank = 0;
        bool found = false;
        
        // Navigate to starting position
        for (int level = MAX_HEIGHT - 1; level >= 0; level--) {
            while (start >= curr_node->next_header.load(std::memory_order_acquire)) {
                curr_node = curr_node->next.get_ptr();
                if (!curr_node) goto retry_range_length;
                
                uint64_t new_version = curr_node->version.load(std::memory_order_acquire);
                if (new_version != version) goto retry_range_length;
                version = new_version;
            }
            
            auto [rank, found_key] = curr_node->find_key_and_check(start);
            current_key_rank = rank;
            if (found_key) {
                found = true;
                break;
            }
            
            if (level > 0) {
                BSkipNodeInternal<traits>* internal = (BSkipNodeInternal<traits>*)curr_node;
                curr_node = internal->get_child_at_rank(current_key_rank);
                if (!curr_node) goto retry_range_length;
                version = curr_node->version.load(std::memory_order_acquire);
            }
        }
        
        // Navigate down to leaf
        while (curr_node->level > 0) {
            BSkipNodeInternal<traits>* internal = (BSkipNodeInternal<traits>*)curr_node;
            curr_node = internal->get_child_at_rank(found ? current_key_rank : 0);
            if (!curr_node) goto retry_range_length;
            version = curr_node->version.load(std::memory_order_acquire);
            if (!found) current_key_rank = curr_node->find_key(start);
        }
        
        // Adjust starting position if start not found
        if (!found) {
            current_key_rank++;
            uint32_t n = curr_node->num_elts.load(std::memory_order_acquire);
            if (current_key_rank == n) {
                curr_node = curr_node->next.get_ptr();
                if (!curr_node) {
                    epoch_manager.exit_epoch();
                    return;
                }
                current_key_rank = 0;
                version = curr_node->version.load(std::memory_order_acquire);
            }
        }
        
        // Apply function to length elements
        BSkipNodeLeaf<traits>* leaf = (BSkipNodeLeaf<traits>*)curr_node;
        uint32_t num_remaining = length;
        
        while (leaf && leaf->get_key_at_rank(current_key_rank) != std::numeric_limits<K>::max() && 
               num_remaining > 0) {
            
            uint32_t n = leaf->num_elts.load(std::memory_order_acquire);
            uint32_t iteration = std::min(n - current_key_rank, num_remaining);
            
            for (uint32_t i = 0; i < iteration; i++) {
                f(leaf->get_key_at_rank(current_key_rank), 
                  leaf->get_value_at_rank(current_key_rank));
                current_key_rank++;
            }
            
            // Check version
            if (leaf->version.load(std::memory_order_acquire) != version) {
                goto retry_range_length;
            }
            
            num_remaining -= iteration;
            
#if STATS
            this->range_length_node_counter++;
#endif
            
            if (num_remaining > 0) {
                leaf = (BSkipNodeLeaf<traits>*)leaf->next.get_ptr();
                if (!leaf) break;
                current_key_rank = 0;
                version = leaf->version.load(std::memory_order_acquire);
            }
        }
        
        // Successfully completed
        epoch_manager.exit_epoch();
        return;
        
        retry_range_length:;
    }
    
    epoch_manager.exit_epoch();
}

// Helper functions remain the same
template <typename traits>
uint32_t BSkip<traits>::flip_coins(typename traits::key_type k)
{
    uint32_t result = 0;
    size_t h = std::hash<typename traits::key_type>{}(k);
    uint64_t flip = h % traits::p;
    while (flip == 0)
    {
        result++;
        if (result > MAX_HEIGHT - 1)
        {
            result = MAX_HEIGHT - 1;
            break;
        }
        h /= traits::p;
        flip = h % traits::p;
    }
    assert(result < MAX_HEIGHT);
    return result;
}

template <typename traits>
uint64_t BSkip<traits>::sum()
{
    auto curr_node = headers[0];
    uint64_t result = 0;
    while (curr_node->get_header() < std::numeric_limits<K>::max())
    {
        result += ((BSkipNodeLeaf<traits> *)curr_node)->sum_keys();
        curr_node = curr_node->next.get_ptr();
    }
    return result;
}

template <typename traits>
uint64_t BSkip<traits>::sum_vals()
{
    auto curr_node = headers[0];
    uint64_t result = 0;
    while (curr_node->get_header() < std::numeric_limits<K>::max())
    {
        result += ((BSkipNodeLeaf<traits> *)curr_node)->sum_vals();
        curr_node = curr_node->next.get_ptr();
    }
    return result;
}

template <typename traits>
void BSkip<traits>::sum_helper(std::vector<uint64_t> &sums,
                               BSkipNode<traits> *node, int level,
                               typename traits::key_type local_max)
{
    assert(node);
    auto next = node->next.get_ptr();
    assert(next);
    
    if (level == 0)
    {
        if (node->next_header.load(std::memory_order_acquire) < local_max)
        {
            sum_helper(sums, next, level, local_max);
        }
        sums[ParallelTools::getWorkerNum() * 8] += ((BSkipNodeLeaf<traits>*)node)->sum_keys();
    }
    else
    {
        BSkipNodeInternal<traits> *curr_node_cast =
            (BSkipNodeInternal<traits> *)node;
        if (curr_node_cast->next_header.load(std::memory_order_acquire) < local_max)
        {
            sum_helper(sums, next, level, local_max);
        }
        
        uint32_t n = node->num_elts.load(std::memory_order_acquire);
        for (uint32_t i = 0; i < n; i++)
        {
            if (i < n - 1)
            {
                sum_helper(sums, curr_node_cast->get_child_at_rank(i), level - 1,
                           node->get_key_at_rank(i + 1));
            }
            else
            {
                sum_helper(sums, curr_node_cast->get_child_at_rank(i), level - 1,
                           node->next_header.load(std::memory_order_acquire));
            }
        }
    }
}

template <typename traits>
uint64_t BSkip<traits>::psum()
{
    std::vector<uint64_t> partial_sums(ParallelTools::getWorkers() * 8);
    int start_level = 2;
    auto top_node = headers[start_level];
    
    while (top_node->get_header() < std::numeric_limits<K>::max())
    {
        BSkipNodeInternal<traits> *top_node_cast =
            (BSkipNodeInternal<traits> *)top_node;
        
        uint32_t n = top_node->num_elts.load(std::memory_order_acquire);
#if CILK
        cilk_for(uint32_t i = 0; i < n; i++)
        {
#else
        for (uint32_t i = 0; i < n; i++)
        {
#endif
            auto curr_node = top_node_cast->get_child_at_rank(i);
            K end;
            if (i < n - 1)
            {
                end = top_node->get_key_at_rank(i + 1);
            }
            else
            {
                end = top_node->next_header.load(std::memory_order_acquire);
            }
            
            while (curr_node->get_header() < end)
            {
                BSkipNodeInternal<traits> *curr_node_cast =
                    (BSkipNodeInternal<traits> *)curr_node;
                
                uint32_t m = curr_node->num_elts.load(std::memory_order_acquire);
#if CILK
                cilk_for(uint32_t j = 0; j < m; j++)
                {
#else
                for (uint32_t j = 0; j < m; j++)
                {
#endif
                    auto curr_leaf = curr_node_cast->get_child_at_rank(j);
                    K leaf_end = 0;
                    if (j < m - 1)
                    {
                        leaf_end = curr_node->get_key_at_rank(j + 1);
                    }
                    else
                    {
                        leaf_end = curr_node->next_header.load(std::memory_order_acquire);
                    }
                    
                    while (curr_leaf->get_header() < leaf_end)
                    {
                        partial_sums[ParallelTools::getWorkerNum() * 8] +=
                            ((BSkipNodeLeaf<traits> *)curr_leaf)->sum_keys();
                        curr_leaf = curr_leaf->next.get_ptr();
                    }
                }
                curr_node = curr_node->next.get_ptr();
            }
        }
        top_node = top_node->next.get_ptr();
    }
    
    uint64_t result = 0;
    for (int i = 0; i < ParallelTools::getWorkers(); i++)
    {
        result += partial_sums[i * 8];
    }
    return result;
}

template <typename traits>
void BSkip<traits>::get_size_stats()
{
    uint64_t elts_per_level[MAX_HEIGHT];
    uint64_t nodes_per_level[MAX_HEIGHT];
    
    for (int level = MAX_HEIGHT - 1; level >= 0; level--)
    {
        auto curr_node = headers[level];
        nodes_per_level[level] = 0;
        elts_per_level[level] = 0;
        
        while (curr_node->get_header() < std::numeric_limits<K>::max())
        {
            nodes_per_level[level]++;
            elts_per_level[level] += curr_node->num_elts.load(std::memory_order_acquire);
            curr_node = curr_node->next.get_ptr();
        }
        nodes_per_level[level]++;
        elts_per_level[level]++;
    }
    
    uint64_t total_elts = 0;
    uint64_t total_nodes = 0;
    double density_per_level[MAX_HEIGHT];
    uint64_t num_internal_nodes = 0;
    
    for (int level = MAX_HEIGHT - 1; level >= 0; level--)
    {
        total_elts += elts_per_level[level];
        total_nodes += nodes_per_level[level];
        if (level > 0)
        {
            num_internal_nodes += nodes_per_level[level];
        }
        
        double density = (double)elts_per_level[level] /
                         (double)(nodes_per_level[level] * traits::MAX_KEYS);
        printf("level %d, elts %lu, nodes %lu, total slots %lu, density = %f\n",
               level, elts_per_level[level], nodes_per_level[level],
               nodes_per_level[level] * traits::MAX_KEYS, density);
        density_per_level[level] = density;
    }
    
    uint64_t internal_size =
        num_internal_nodes * sizeof(BSkipNodeInternal<traits>);
    uint64_t size_in_bytes =
        internal_size + nodes_per_level[0] * sizeof(BSkipNodeLeaf<traits>);
    double overhead = (double)internal_size / (double)size_in_bytes;
    double overall_density =
        (double)total_elts / (double)(total_nodes * traits::MAX_KEYS);
    double leaf_avg = (double)elts_per_level[0] / (double)nodes_per_level[0];
    
    double var_numerator = 0;
    uint32_t min_leaf = std::numeric_limits<uint32_t>::max();
    uint32_t max_leaf = std::numeric_limits<uint32_t>::min();
    auto curr_node = headers[0];
    
    while (curr_node->get_header() < std::numeric_limits<K>::max())
    {
        uint32_t n = curr_node->num_elts.load(std::memory_order_acquire);
        if (n < min_leaf)
        {
            min_leaf = n;
        }
        if (n > max_leaf)
        {
            max_leaf = n;
        }
        double x = (double)n - leaf_avg;
        var_numerator += (x * x);
        curr_node = curr_node->next.get_ptr();
    }
    
    double var = var_numerator / (double)(nodes_per_level[0]);
    double stdev = sqrt(var);
    printf("avg %f, min %u, max %u, var %f, stddev %f\n", leaf_avg, min_leaf,
           max_leaf, var, stdev);
    
    FILE *file = fopen("bskip_sizes.csv", "a+");
    fprintf(file,
            "%lu,%lu,%d,%lu,%lu,%f,%f,%lu,%f,%lu,%f,%lu,%f,%lu,%f,%lu,%f,%f,%u,%"
            "u,%f,%f\n",
            elts_per_level[0], traits::MAX_KEYS, MAX_HEIGHT, internal_size,
            size_in_bytes, overhead, overall_density, nodes_per_level[4],
            density_per_level[4], nodes_per_level[3], density_per_level[3],
            nodes_per_level[2], density_per_level[2], nodes_per_level[1],
            density_per_level[1], nodes_per_level[0], density_per_level[0],
            leaf_avg, min_leaf, max_leaf, var, stdev);
    fclose(file);
}

template <typename traits>
void BSkip<traits>::get_avg_comparisons()
{
    // Not meaningful in lock-free version
    printf("avg comparisons = N/A (lock-free version)\n");
}

template <typename traits>
void BSkip<traits>::validate_structure()
{
    int violations = 0;
    for (int level = MAX_HEIGHT - 1; level >= 0; level--)
    {
        auto curr_node = headers[level];
        while (curr_node->get_header() < std::numeric_limits<K>::max())
        {
            auto next = curr_node->next.get_ptr();
            if (next) {
                tbassert(curr_node->get_header() < next->get_header(),
                         "level %d, curr node header %lu, next node header %lu\n",
                         level, (unsigned long)curr_node->get_header(), 
                         (unsigned long)next->get_header());
            }
            
            uint32_t n = curr_node->num_elts.load(std::memory_order_acquire);
            for (uint32_t i = 1; i < n; i++)
            {
                tbassert(curr_node->get_key_at_rank(i - 1) <
                             curr_node->get_key_at_rank(i),
                         "level %d, elts[%u] = %lu, elts[%u] = %lu\n", level, i - 1,
                         (unsigned long)curr_node->get_key_at_rank(i - 1), i,
                         (unsigned long)curr_node->get_key_at_rank(i));
            }
            
            if (next && next->get_header() < std::numeric_limits<K>::max()) {
                K next_hdr = curr_node->next_header.load(std::memory_order_acquire);
                if (next_hdr != next->get_header()) {
                    violations++;
                }
            }
            curr_node = next;
        }
    }
    printf("violations = %d\n", violations);
}

#endif
// EVOLVE-BLOCK-END
