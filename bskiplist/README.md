# B-skiplist

## Compilation:

To compile the code for throughput, run `make`. To compile the code for both throughput and latency, run `make LATENCY=1`

## Execution

After compiling, run `./ycsb <path to ycsb files> <workload> <thread number> <output file>`

Example command: `./ycsb /home/eddy/repo/ycsb/ a 16 out.txt`

The througput or/and latency will be printed in the terminal


./ycsb /mydata/skip_data/uniform/ a 32 out.txt  # skip_data stays at /mydata


cloudlab Image: urn:publicid:IDN+wisc.cloudlab.us+image+dirr-PG0:EvolveDataStructure:1