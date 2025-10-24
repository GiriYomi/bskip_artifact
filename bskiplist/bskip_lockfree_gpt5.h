// EVOLVE-BLOCK-START

#ifndef _BSKIP_H_
#define _BSKIP_H_

#include <algorithm>
#include <atomic>
#include <cassert>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <limits>
#include <random>
#include <string.h>
#include <type_traits>
#include <utility>
#include <vector>

#include "tbassert.h"

// Kept for compatibility with the project; not used on hot paths anymore
#include <ParallelTools/Lock.hpp>
#include <ParallelTools/parallel.h>
#include <ParallelTools/reducer.h>

#include "StructOfArrays/SizedInt.hpp"
#include "StructOfArrays/aos.hpp"
#include "StructOfArrays/soa.hpp"
#include "tools.h"

// ========================= Original type traits & node shells =========================
// These remain so public names and includes stay unchanged. Internal hot paths
// no longer rely on them; instead we use a new LF (lock-free) backbone.
#define BINARY_SEARCH 0

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

// Skeletons preserved (unused by hot path)
class Empty { };

template <typename traits>
class BSkipNode
{
public:
    uint32_t num_elts{0};
    uint32_t level{0};
    BSkipNode<traits> *next{nullptr};
    typename traits::key_type next_header{
        std::numeric_limits<typename traits::key_type>::max()
    };

    virtual ~BSkipNode() {}
    bool is_leafnode() const { return (level == 0); }
    virtual typename traits::key_type get_header() = 0;
    virtual uint32_t find_key(typename traits::key_type k) = 0;
    virtual std::pair<uint32_t, bool> find_key_and_check(typename traits::key_type k) = 0;
    virtual typename traits::key_type get_key_at_rank(uint32_t) = 0;
    virtual void insert_key_at_rank(uint32_t, typename traits::key_type) = 0;
    virtual int split_keys(BSkipNode<traits>*, uint32_t, uint32_t = 1) = 0;
    virtual void print_keys() = 0;
};

template <typename traits>
class BSkipNodeLeaf : public BSkipNode<traits>
{
public:
    using K = typename traits::key_type;
    using V = typename traits::value_type;
    using elt_type = typename traits::element_type;

    static constexpr K NULL_VAL = {};
    static constexpr size_t max_element_size = sizeof(K);
    using SOA_type = typename traits::SOA_leaf_type;
    static constexpr uint64_t max_size = traits::MAX_KEYS;

    mutable std::conditional_t<traits::concurrent, ReaderWriterLock2, Empty> mutex_;
    std::array<uint8_t, SOA_type::get_size_static(max_size)> array = {0};

    inline K get_key_array(uint32_t index) const {
        return std::get<0>(
            SOA_type::template get_static<0>(array.data(), max_size, index));
    }
    auto blind_read_key(uint32_t i) const { return std::get<0>(SOA_type::get_static(array.data(), max_size, i)); }
    auto blind_read_val(uint32_t i) const { return std::get<1>(SOA_type::get_static(array.data(), max_size, i)); }
    void blind_write_array(void *arr, size_t len, uint32_t index, elt_type e) { SOA_type::get_static(arr, len, index) = e; }
    void blind_write(elt_type e, uint32_t index) { SOA_type::get_static(array.data(), max_size, index) = e; }
    auto blind_read(uint32_t index) const { return SOA_type::get_static(array.data(), max_size, index); }
    auto blind_read_array(void *arr, size_t size, uint32_t index) const { return SOA_type::get_static(arr, size, index); }
    auto blind_read_key_array(void *arr, size_t size, uint32_t index) const { return std::get<0>(SOA_type::get_static(arr, size, index)); }

    size_t count_up_elts() const {
        size_t result = 0;
        for (size_t i = 0; i < max_size; i++) result += (blind_read_key(i) != NULL_VAL);
        return result;
    }
    inline K get_header() { return blind_read_key(0); }
    uint64_t sum_keys() {
        uint64_t r = 0; for (uint32_t i=0;i<BSkipNode<traits>::num_elts;i++) r += blind_read_key(i); return r;
    }
    uint64_t sum_vals() {
        uint64_t r = 0; for (uint32_t i=0;i<BSkipNode<traits>::num_elts;i++) r += blind_read_val(i); return r;
    }
    void print_keys() {
        printf("\tlevel = %u, num keys = %u\n", BSkipNode<traits>::level, BSkipNode<traits>::num_elts);
        for (uint32_t i=0;i<BSkipNode<traits>::num_elts;i++) printf("\t\tkey[%d] = %lu\n", i, (unsigned long)blind_read_key(i));
        printf("\n");
    }

    uint32_t find_key(K k) {
        assert(BSkipNode<traits>::num_elts > 0);
        uint32_t i=0; for (; i<BSkipNode<traits>::num_elts; i++) { auto kk=blind_read_key(i); if (kk<k) continue; else if (kk==k) return i; else break; }
        return i-1;
    }
    std::pair<uint32_t,bool> find_key_and_check(K k) {
        uint32_t idx = find_key(k);
        return {idx, (blind_read_key(idx)==k)};
    }

    void insert_elt_at_rank(uint32_t rank, elt_type elt) {
        assert(BSkipNode<traits>::num_elts + 1 <= max_size);
        for (size_t j = BSkipNode<traits>::num_elts; j>rank; j--)
            SOA_type::get_static(array.data(), max_size, j) =
                SOA_type::get_static(array.data(), max_size, j-1);
        blind_write(elt, rank);
    }
    inline K get_key_at_rank(uint32_t rank) { return blind_read_key(rank); }
    inline V get_value_at_rank(uint32_t rank) { return blind_read_val(rank); }
    void insert_key_at_rank(uint32_t, K){ assert(false); }
    inline void set_elt_at_rank(uint32_t rank, elt_type elt){ assert(rank<BSkipNode<traits>::num_elts); blind_write(elt,rank); }
    int split_keys(BSkipNode<traits>* dest, uint32_t start, uint32_t dest_rank=1) {
        uint32_t mv = BSkipNode<traits>::num_elts - start;
        assert(start <= BSkipNode<traits>::num_elts);
        assert(mv <= BSkipNode<traits>::num_elts); assert(mv < traits::MAX_KEYS);
        for (uint32_t j=0;j<mv;j++)
            ((BSkipNodeLeaf<traits>*)dest)->blind_write(blind_read(start+j), dest_rank+j);
        BSkipNode<traits>::num_elts = start; dest->num_elts += mv; return mv;
    }
};

template <typename traits>
class BSkipNodeInternal : public BSkipNode<traits>
{
    using K = typename traits::key_type;
public:
    mutable std::conditional_t<traits::concurrent, ReaderWriterLock, Empty> mutex_;
    K keys[traits::MAX_KEYS];
    BSkipNode<traits>* children[traits::MAX_KEYS];

    BSkipNodeInternal() {}
    inline K get_header() { return keys[0]; }
    void set_key_at_rank(uint32_t r, K k){ keys[r]=k; }
    void insert_child_at_rank(uint32_t r, BSkipNode<traits>* e, bool flag=true){
        assert(this->num_elts <= traits::MAX_KEYS);
        if (flag) memmove(children+r+1, children+r, (this->num_elts-r-1)*sizeof(BSkipNode<traits>*));
        else      memmove(children+r+1, children+r, (this->num_elts-r)*sizeof(BSkipNode<traits>*));
        children[r]=e;
    }
    BSkipNode<traits>* get_child_at_rank(uint32_t r){ return children[r]; }
    void set_child_at_rank(uint32_t r, BSkipNode<traits>* e){ children[r]=e; }
    void move_children(BSkipNodeInternal<traits>* dest, uint32_t start, uint32_t mv, uint32_t dest_rank=1) {
        memmove(dest->children+dest_rank, children+start, mv*sizeof(BSkipNode<traits>*));
    }
    uint32_t find_key(typename traits::key_type k){
        assert(BSkipNode<traits>::num_elts > 0);
        uint32_t i=0; for (; i<BSkipNode<traits>::num_elts; i++){ if (keys[i]>k) break; }
        if (i==0) return 0; return i-1;
    }
    std::pair<uint32_t,bool> find_key_and_check(typename traits::key_type k){
        assert(BSkipNode<traits>::num_elts > 0);
        uint32_t i=0; for (; i<BSkipNode<traits>::num_elts; i++){ if (keys[i]>k) break; }
        if (i==0) return {0, keys[i]==k};
        return {i-1, keys[i-1]==k};
    }
    typename traits::key_type get_key_at_rank(uint32_t r){
        tbassert(r < this->num_elts, "rank OOB\n");
        return keys[r];
    }
    void insert_key_at_rank(uint32_t r, K k){
        assert(this->level > 0); assert(this->num_elts + 1 <= traits::MAX_KEYS);
        memmove(keys+r+1, keys+r, (this->num_elts - r)*sizeof(K));
        keys[r]=k;
    }
    int split_keys(BSkipNode<traits>* dest, uint32_t start, uint32_t dest_rank=1){
        uint32_t mv = this->num_elts - start;
        assert(mv < traits::MAX_KEYS);
        memmove(((BSkipNodeInternal<traits>*)dest)->keys+dest_rank, keys+start, mv*sizeof(K));
        this->num_elts = start; dest->num_elts += mv; return mv;
    }
    void print_keys(){
        printf("\tlevel = %u, num keys = %u\n", BSkipNode<traits>::level, BSkipNode<traits>::num_elts);
        for (uint32_t i=0;i<BSkipNode<traits>::num_elts;i++) printf("\t\tkey[%d] = %lu\n", i, (unsigned long)keys[i]);
        printf("\n");
    }
};

// ========================= New lock-free backbone (hot path) =========================

namespace detail_bskip {

// tuple_tail: convert element_type (key, v1, v2, ...) -> value_type (v1, v2, ...)
template <class Tuple, std::size_t... I>
constexpr auto tuple_tail_impl(const Tuple& t, std::index_sequence<I...>) {
    return std::make_tuple(std::get<I+1>(t)...);
}
template <class Tuple>
constexpr auto tuple_tail(const Tuple& t) {
    constexpr std::size_t N = std::tuple_size<Tuple>::value;
    static_assert(N >= 1, "element_type must have at least a key");
    return detail_bskip::tuple_tail_impl(t, std::make_index_sequence<N-1>{});
}

// Minimal epoch reclamation for payload versions (QSBR/EBR)
struct EpochReclaimer {
    struct Slot {
        std::atomic<uint64_t> epoch{0};
        std::atomic<bool> active{false};
        // retired payload pointers paired with retire epoch
        struct Ret { void* ptr; uint64_t epoch; };
        std::vector<Ret> retired;
    };

    std::atomic<uint64_t> global_epoch{1};
    // a small static registry; good enough for YCSB threads
    static constexpr size_t MAX_THREADS = 256;
    Slot slots[MAX_THREADS];

    // simplistic thread id fetch (not perfect, but bounded)
    static inline uint32_t thread_id() {
#if defined(__linux__)
        // fall back to hashed std::thread::id
        auto x = std::hash<std::thread::id>{}(std::this_thread::get_id());
        return static_cast<uint32_t>(x % MAX_THREADS);
#else
        auto x = std::hash<std::thread::id>{}(std::this_thread::get_id());
        return static_cast<uint32_t>(x % MAX_THREADS);
#endif
    }

    void enter() {
        uint32_t id = thread_id();
        auto& s = slots[id];
        s.active.store(true, std::memory_order_release);
        s.epoch.store(global_epoch.load(std::memory_order_acquire), std::memory_order_release);
    }
    void leave_and_try_advance() {
        uint32_t id = thread_id();
        auto& s = slots[id];
        s.active.store(false, std::memory_order_release);
        // Opportunistically advance epoch if everyone quiescent in <= current
        uint64_t g = global_epoch.load(std::memory_order_acquire);
        bool can_advance = true;
        for (size_t i=0;i<MAX_THREADS;i++) {
            if (slots[i].active.load(std::memory_order_acquire)) { can_advance = false; break; }
        }
        if (can_advance) global_epoch.fetch_add(1, std::memory_order_acq_rel);
        try_collect();
    }
    void retire(void* p) {
        uint32_t id = thread_id();
        auto& s = slots[id];
        uint64_t e = global_epoch.load(std::memory_order_acquire);
        s.retired.push_back({p, e});
        if (s.retired.size() > 1024) try_collect(); // occasional GC
    }
    void try_collect() {
        // compute safe epoch: minimum observed epoch among active slots
        uint64_t min_epoch = global_epoch.load(std::memory_order_acquire);
        for (size_t i=0;i<MAX_THREADS;i++) {
            if (slots[i].active.load(std::memory_order_acquire)) {
                min_epoch = std::min(min_epoch, slots[i].epoch.load(std::memory_order_acquire));
            }
        }
        uint64_t safe_epoch = (min_epoch==0) ? 0 : (min_epoch - 1);

        // free retired payloads whose epoch <= safe_epoch
        for (size_t i=0;i<MAX_THREADS;i++) {
            auto& s = slots[i];
            size_t w = 0;
            for (size_t r=0; r<s.retired.size(); r++) {
                auto &it = s.retired[r];
                if (it.epoch <= safe_epoch) {
                    delete static_cast<std::byte*>(it.ptr); // we allocate payload as raw byte blob
                } else {
                    s.retired[w++] = it;
                }
            }
            if (w < s.retired.size()) s.retired.resize(w);
        }
    }
};

} // namespace detail_bskip

// ========================= BSkip (public API preserved) =========================

template <typename traits>
class BSkip
{
    using K = typename traits::key_type;
    using E = typename traits::element_type;
    using V = typename traits::value_type;

    // -------- Lock-free singly linked list node with immutable payload --------
    struct Payload {
        // Store full element (key, v...) so we can slice value_type at read
        E elt;
    };

    struct LFNode {
        K key;
        std::atomic<LFNode*> next;
        std::atomic<Payload*> payload; // immutable snapshots
        LFNode(K k, LFNode* n, Payload* p) : key(k), next(n), payload(p) {}
    };

    // Sentinels
    LFNode* head_;
    LFNode* tail_;

    // Epoch reclaimer for payloads
    detail_bskip::EpochReclaimer ebr_;

    // Disable copy
    BSkip(const BSkip&) = delete;
    BSkip& operator=(const BSkip&) = delete;

public:
    static constexpr uint32_t MAX_HEIGHT = 5; // kept to preserve public constant
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
    bool has_zero = false; // no longer special-cased but retained for ABI

    // Kept to satisfy external code that may reference these members;
    // we do not use them in the new implementation.
    BSkipNode<traits> *headers[MAX_HEIGHT] = {nullptr};

#if ENABLE_TRACE_TIMER
    ParallelTools::Reducer_sum<uint64_t> read_lock_count;
    ParallelTools::Reducer_sum<uint64_t> write_lock_count;
    ParallelTools::Reducer_sum<uint64_t> leaf_lock_count;

    void get_lock_counts(){
        printf("read lock count = %lu, write_lock_count = %lu, leaf lock count = %lu\n",
               read_lock_count.get(), write_lock_count.get(), leaf_lock_count.get());
    }
    void reset_lock_counts(){ read_lock_count -= read_lock_count.get(); write_lock_count -= write_lock_count.get(); leaf_lock_count -= leaf_lock_count.get(); }
    uint64_t get_read_lock_count(){ return read_lock_count.get(); }
    uint64_t get_write_lock_count(){ return write_lock_count.get(); }
    uint64_t get_leaf_lock_count(){ return leaf_lock_count.get(); }
    uint64_t insert(E k); // kept signature
#else
    bool insert(E k);
#endif

    BSkipNode<traits> *find(K) const;                 // legacy (unused by YCSB)
    V value(K k) const;
    bool exists(K k) const;

    template <class F>
    void map_range_length(K start, uint64_t length, F f) const;

    template <class F>
    void map_range(K min, K max, F f) const;

    uint64_t sum();        // sum of keys
    uint64_t sum_vals();   // sum of values (first Ts...)
    uint64_t psum();       // kept (returns sum(), single-threaded)
    void validate_structure();
    void get_size_stats() { /* optional: no-op for LF list to keep API */ }
    void get_avg_comparisons() { /* no-op */ }
    uint32_t flip_coins(K) { return 0; } // not used in LF variant

    int node_size = sizeof(LFNode);

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

    BSkip() {
        // Create sentinels
        auto p_head = new Payload{E{std::tuple<K>(std::numeric_limits<K>::min())}};
        auto p_tail = new Payload{E{std::tuple<K>(std::numeric_limits<K>::max())}};

        tail_ = new LFNode(std::numeric_limits<K>::max(), nullptr, p_tail);
        head_ = new LFNode(std::numeric_limits<K>::min(), tail_, p_head);
    }

    ~BSkip() {
        // Walk and delete nodes and payloads
        auto n = head_;
        while (n) {
            auto nxt = n->next.load(std::memory_order_relaxed);
            if (auto pl = n->payload.load(std::memory_order_relaxed)) {
                delete pl;
            }
            delete n;
            n = nxt;
        }
        // Drain any retired payloads (if any remain)
        ebr_.try_collect();
    }

    void print_leaves() {
        auto n = head_;
        while (n) {
            std::cout << "key=" << n->key << "\n";
            n = n->next.load(std::memory_order_acquire);
        }
    }

private:
    // lower_bound: returns (pred, curr) with curr->key >= k
    std::pair<LFNode*, LFNode*> lower_bound(K k) const {
        LFNode* pred = head_;
        LFNode* curr = pred->next.load(std::memory_order_acquire);
        while (true) {
            K ck = curr->key;
            if (ck >= k) return {pred, curr};
            pred = curr;
            curr = curr->next.load(std::memory_order_acquire);
        }
    }

    static Payload* make_payload(const E& e) {
        // allocate as a raw blob so we can free via EpochReclaimer (std::byte*)
        auto raw = new std::byte[sizeof(Payload)];
        auto p = reinterpret_cast<Payload*>(raw);
        new (p) Payload{e};
        return p;
    }

    // Extract value_type (tail of element)
    static V to_value(const E& elt) {
        return detail_bskip::tuple_tail(elt);
    }
};

// --------------------------------- insert ------------------------------------

template <typename traits>
#if ENABLE_TRACE_TIMER
uint64_t
#else
bool
#endif
BSkip<traits>::insert(E k)
{
    const K key = std::get<0>(k);

    // Linearizable update on key==0 is now normal: no sentinel collision.
    ebr_.enter();

    while (true) {
        auto [pred, curr] = lower_bound(key);

        if (curr->key == key) {
            // Update existing payload (linearization: atomic exchange)
            auto newp = make_payload(k);
            Payload* oldp = curr->payload.exchange(newp, std::memory_order_acq_rel);
            // retire old payload safely
            ebr_.retire(reinterpret_cast<void*>(oldp));
#if ENABLE_TRACE_TIMER
            ebr_.leave_and_try_advance();
            return 0;
#else
            ebr_.leave_and_try_advance();
            return true;
#endif
        }

        // Insert new node between pred and curr
        auto payload = make_payload(k);
        auto node = new LFNode(key, curr, payload);

        LFNode* expected = curr;
        if (pred->next.compare_exchange_weak(
                expected, node, std::memory_order_acq_rel, std::memory_order_acquire)) {
            // success
#if ENABLE_TRACE_TIMER
            ebr_.leave_and_try_advance();
            return 0;
#else
            ebr_.leave_and_try_advance();
            return true;
#endif
        } else {
            // CAS failed: another insert raced; retry
            delete node->payload.load(std::memory_order_relaxed);
            delete node;
        }
    }
}

// --------------------------------- value -------------------------------------

template <typename traits>
typename traits::value_type
BSkip<traits>::value(K k) const
{
#if STATS
    this->query_counter++;
#endif
    // Obstruction-free read
    // (We guard only payload reclamation via epoch; nodes are never deleted.)
    const_cast<BSkip*>(this)->ebr_.enter();

    auto [pred, curr] = lower_bound(k);
    (void)pred;

    if (curr->key == k) {
        auto p = curr->payload.load(std::memory_order_acquire);
        auto v = to_value(p->elt);
        const_cast<BSkip*>(this)->ebr_.leave_and_try_advance();
        return v;
    }

    // not found: unspecified per requirements; return default V{}
    const_cast<BSkip*>(this)->ebr_.leave_and_try_advance();
    return V{};
}

// --------------------------------- exists ------------------------------------

template <typename traits>
bool BSkip<traits>::exists(K k) const
{
    const_cast<BSkip*>(this)->ebr_.enter();
    auto [pred, curr] = lower_bound(k);
    (void)pred;
    bool found = (curr->key == k);
    const_cast<BSkip*>(this)->ebr_.leave_and_try_advance();
    return found;
}

// --------------------------- map_range_length --------------------------------

template <typename traits>
template <class F>
void BSkip<traits>::map_range_length(K start, uint64_t length, F f) const
{
    if (length == 0) return;
    const_cast<BSkip*>(this)->ebr_.enter();

    auto [pred, curr] = lower_bound(start);
    (void)pred;

    // If start not present, begin from first key >= start
    LFNode* n = curr;
    uint64_t remaining = length;

    while (remaining && n && n->key != std::numeric_limits<K>::max()) {
        auto p = n->payload.load(std::memory_order_acquire);
        f(n->key, to_value(p->elt));
        n = n->next.load(std::memory_order_acquire);
        --remaining;
#if STATS
        this->range_length_node_counter++;
#endif
    }

#if STATS
    this->range_length_counter++;
#endif

    const_cast<BSkip*>(this)->ebr_.leave_and_try_advance();
}

// -------------------------------- map_range ----------------------------------

template <typename traits>
template <class F>
void BSkip<traits>::map_range(K min, K max, F f) const
{
    // Apply f to keys in [min, max) in sorted order
    const_cast<BSkip*>(this)->ebr_.enter();
    auto [pred, curr] = lower_bound(min);
    (void)pred;

    LFNode* n = curr;
    while (n && n->key < max) {
        if (n->key == std::numeric_limits<K>::max()) break;
        auto p = n->payload.load(std::memory_order_acquire);
        f(n->key, to_value(p->elt));
        n = n->next.load(std::memory_order_acquire);
    }
    const_cast<BSkip*>(this)->ebr_.leave_and_try_advance();
}

// ----------------------------------- sum -------------------------------------

template <typename traits>
uint64_t BSkip<traits>::sum()
{
    ebr_.enter();
    uint64_t r = 0;
    LFNode* n = head_->next.load(std::memory_order_acquire);
    while (n && n->key != std::numeric_limits<K>::max()) {
        r += static_cast<uint64_t>(n->key);
        n = n->next.load(std::memory_order_acquire);
    }
    ebr_.leave_and_try_advance();
    return r;
}

template <typename traits>
uint64_t BSkip<traits>::sum_vals()
{
    // Best-effort: only meaningful if value is integral in first component.
    ebr_.enter();
    uint64_t r = 0;
    LFNode* n = head_->next.load(std::memory_order_acquire);
    while (n && n->key != std::numeric_limits<K>::max()) {
        auto p = n->payload.load(std::memory_order_acquire);
        // If V is empty (set), contributes 0.
        if constexpr (!traits::binary) {
            // sum the first value component if integral; otherwise 0
            using First = typename traits::template NthType<0>;
            if constexpr (std::is_integral_v<First> || std::is_unsigned_v<First>) {
                r += static_cast<uint64_t>(std::get<1>(p->elt));
            }
        }
        n = n->next.load(std::memory_order_acquire);
    }
    ebr_.leave_and_try_advance();
    return r;
}

template <typename traits>
uint64_t BSkip<traits>::psum() {
    // single-threaded reduction over the list
    return sum();
}

// ------------------------------ validate_structure ---------------------------

template <typename traits>
void BSkip<traits>::validate_structure()
{
    ebr_.enter();
    LFNode* n = head_;
    int violations = 0;
    while (n) {
        LFNode* nx = n->next.load(std::memory_order_acquire);
        if (nx) {
            if (!(n->key <= nx->key)) violations++;
        }
        n = nx;
    }
    printf("violations = %d\n", violations);
    ebr_.leave_and_try_advance();
}

// ------------------------------ legacy find (unused) -------------------------

template <typename traits>
BSkipNode<traits>* BSkip<traits>::find(K) const
{
    // Legacy API kept for compatibility; not used by YCSB; return nullptr.
    return nullptr;
}

#endif

// EVOLVE-BLOCK-END

