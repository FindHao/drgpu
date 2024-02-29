# DrGPU


## Download DrGPU


```
git clone git@github.com:FindHao/drgpu.git
```



## Prerequisites

DrGPU has the following minimum requirements, which must be installed before DrGPU is run:

1. Python3
2. graphviz
3. python packages: pandas, json, numpy, 
4. Nsight Compute  2020.3.0 +
5. Nsight System, CUDA 11.0+

These requirements can be easily installed on most modern Linux systems. You can use 

```
sudo apt install graphviz python3 python3-pip 
```

to install `python3` and `graphviz`. 



## Get Profile Reports

Let's take `b+tree` as an example. 

First, decide which kernel is going to be profiled. The execution time distribution of kernels can be found in the profile report of Nsight System.

```
nsys profile --stats=true ./b+tree.out file ../data/mil.txt command ../data/command.txt
```

Second, use the script `drgpu_collector.sh` to collect the necessary hardware counters via the following command.

```
drgpu_collector.sh -k findRangeK -o btree ./b+tree.out file ../data/mil.txt command ../data/command.txt
```

In this example, `findRangeK` is the target kernel. There will be two new files generated in current folder, `btree.ncu-rep` and `btree.csv`.

## Get Source Code Line Mapping with Stall Reasons[Optional]

Because of the limitation of ncu, currently we have to export the source code mapping with stall reasons manually. First, use ncu-gui to open `btree.ncu-rep` and change the page to `Source` by clicking the page selection on the left up corner. Then change the View to `Source` and click the down arrow on the right up  corner. Choose `Export to CSV` to save the current source line mapping after typed the output name. In this example, we use `btree_s.csv` as the source code mapping file.

This file is not required because some suggestions do not need specific source code changing rather than launching or compilation configurations. Also, we need to add `-g - lineinfo` into the makefile to get the correct source code line mapping.

## Get Performance Analysis Tree

Now, we have `btree.csv` and `btree_s.csv`. Run the following commands to generate the performance analysis tree.

```bash
drgpu_entry.py -i btree.csv -s btree_s.csv -c gtx1650 -o btree
```

DrGPU will generate two files in current folder,  `dots/btree`  and `dots/btree.svg`.



According to suggestions and values in the performance analysis tree, you can try to optimize your code.

More detailed usage could be found in other pages in this manual.

## Citation

If you use our research work in your projects, we kindly request that you cite the following paper:
```
@inproceedings{hao2023drgpu,
  title={DrGPU: A Top-Down Profiler for GPU Applications},
  author={Hao, Yueming and Jain, Nikhil and Van der Wijngaart, Rob and Saxena, Nirmal and Fan, Yuanbo and Liu, Xu},
  booktitle={Proceedings of the 2023 ACM/SPEC International Conference on Performance Engineering},
  pages={43--53},
  year={2023}
}
```

