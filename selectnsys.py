#!/usr/bin/python3
from sys import argv
import pandas as pd
import os
import re
import argparse


reports_with_path = {}
execute_name = ''
execute_times = 0
prefix_path = ''
output_prefix= ''


def get_execute_name(reports_path, a_execute_name=''):
    global reports_with_path, execute_name, execute_times, prefix_path, output_prefix
    reg = re.compile(r"report(\d+)")
    # reports_path always end with /reports/
    tmp_report_path = reports_path
    if reports_path.endswith('/'):
        tmp_report_path=tmp_report_path[:-1]
    output_prefix = os.path.basename(tmp_report_path[:-8])
    if a_execute_name:
        execute_name = a_execute_name

    for parent, dirnames, filenames in os.walk(reports_path,  followlinks=True):
        for filename in filenames:
            file_path = os.path.join(parent, filename)
            reports_with_path[filename] = file_path
            # print('file name：%s' % filename)
            # print('full path of this file：%s\n' % file_path)
            if not execute_name and filename.endswith(".qdrep"):
                execute_name = filename[:-6].split("_")[1]
            if not prefix_path:
                prefix_path = parent
            result = reg.findall(filename)
            execute_times = max(int(result[0]), execute_times)
    print("execute_name, execute_times, prefix_path, output_prefix")
    print(execute_name, execute_times, prefix_path, output_prefix)

def gpu_kernel_time():

    k = None
    final = pd.DataFrame()
    for i in range(1, execute_times+1):
        gpukernelsum = prefix_path + "/report%d_%s_gpukernsum.csv" % (i, execute_name)
        kernel_time = pd.read_csv(gpukernelsum)
        need_data = kernel_time[['Name', 'Total Time (ns)']]
        if i == 1:
            k = need_data
        else:
            k = pd.merge(k, need_data, how='outer', on=['Name'])

    final = pd.DataFrame()
    final['Name'] = k.loc[:, 'Name']
    value = k.iloc[:, 1:]
    mean_avg = value.mean(axis=1)
    final['Kenerl Time (ns)'] = mean_avg
    final = final.append(
        {'Name': 'sum_above', 'Kenerl Time (ns)': final.iloc[:, 1:].sum().tolist()[0]}, ignore_index=True)
    final.to_csv(output_prefix + "_kernel_time.csv")


def cuda_api():
    k = None
    final = pd.DataFrame()
    for i in range(1, execute_times+1):
        gpukernelsum = prefix_path + "/report%d_%s_cudaapisum.csv" % (i, execute_name)
        kernel_time = pd.read_csv(gpukernelsum)
        need_data = kernel_time[['Name', 'Total Time (ns)']]
        if i == 1:
            k = need_data
        else:
            k = pd.merge(k, need_data, how='outer', on=['Name'])

    final = pd.DataFrame()
    final['Name'] = k.loc[:, 'Name']
    value = k.iloc[:, 1:]
    mean_avg = value.mean(axis=1)
    final['Kenerl Time (ns)'] = mean_avg
    final = final.append(
        {'Name': 'sum_above', 'Kenerl Time (ns)': final.iloc[:, 1:].sum().tolist()[0]}, ignore_index=True)
    final.to_csv(output_prefix + "_cudaapi.csv")


def gpu_mem_size():
    k = None
    final = pd.DataFrame()
    for i in range(1, execute_times+1):
        gpukernelsum = prefix_path + \
            "/report%d_%s_gpumemsizesum.csv" % (i, execute_name)
        kernel_time = pd.read_csv(gpukernelsum)
        need_data = kernel_time[['Operation', 'Total']]
        if i == 1:
            k = need_data
        else:
            k = pd.merge(k, need_data, how='outer', on=['Operation'])

    final = pd.DataFrame()
    final['Operation'] = k.loc[:, 'Operation']
    value = k.iloc[:, 1:]
    mean_avg = value.mean(axis=1)
    final['Total'] = mean_avg
    final = final.append(
        {'Operation': 'sum_above', 'Total': final.iloc[:, 1:].sum().tolist()[0]}, ignore_index=True)
    final.to_csv(output_prefix + "_memsize.csv")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--report-path', metavar='The path of nsys reports.',
                        required=True, dest='report_path', action='store')
    parser.add_argument('-e', '--execute_name',
                        metavar='report1_XXX_gpukernsum.csv, the middle XXX',
                        required=False, dest='execute_name', action='store')

    args = parser.parse_args()
    get_execute_name(args.report_path, args.execute_name)
    
    gpu_kernel_time()
    cuda_api()
    gpu_mem_size()
