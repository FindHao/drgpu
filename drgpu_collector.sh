#!/bin/bash

usage()
{
    cat <<EOF
Usage:
    drgpu_collector [profiling options] [executable] [executable options]
    profiling options:
    -h help
    -k kernel name
    -o profiling report name
EOF
    exit 0
}

while test "x$1" != x
do
  arg="$1" ; shift
  case "$arg" in
    -k)
      export Kernel_name=$1
      shift
      ;;
    -o)
      export Profile_output=$1
      shift
      ;;
    -h)
      usage
      exit
      ;;
    * )
      set -- "$arg" "$@"
      break
      ;;
  esac
done

DRGPU_EXEC=$1
DRGPU_ARGS="${*:2}"
#--kernel-name-base mangled

if [ ! -z "${Kernel_name}" ]
then
kernel_name_cmd="--kernel-name ${Kernel_name}"
fi

if [ -z "${Profile_output}" ]
then
  Profile_output="tmp"
  echo "output to tmp.ncu-rep and tmp.csv"
fi

ncu -f   --target-processes all -c 1  --export ${Profile_output} --import-source=yes ${kernel_name_cmd} --metrics regex:sm__inst_executed_pipe_[^.]*.avg.pct_of_peak_sustained_active$,regex:sm__sass_thread_inst_executed_op.*sum$,regex:l1tex__t_set_.*_pipe_lsu_mem_global_op_ld.sum$,regex:l1tex__t_set_accesses.sum$,regex:l1tex__t_requests.sum$,regex:l1tex__m_xbar2l1tex_read_sectors.sum$,sm__average_thread_inst_executed_pred_on_per_inst_executed_realtime,regex:sm__sass_inst_executed.*sum$,regex:sm__inst_issued.avg.per_cycle_active$,regex:.*throughput.avg.pct_of_peak_sustained_active$,regex:.*throughput.avg.pct_of_peak_sustained_elapsed$  --page raw --set full ${DRGPU_EXEC} ${DRGPU_ARGS}

ncu --csv --page raw -i ${Profile_output}.ncu-rep > ${Profile_output}.csv

