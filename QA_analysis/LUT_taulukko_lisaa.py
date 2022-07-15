# -*- coding: utf-8 -*-
"""Taman koodin ajamalla saa lisattua LUT taulukkoon antureita"""
import os
from glob import glob
import time
import argparse
import yaml
import pydicom
from QA_analysis.utils.LUT_table_codes import extract_parameters
import pandas as pd


def dir_path(string):
    if os.path.isdir(string):
        return string
    else:
        raise NotADirectoryError(string)


# Parser:
parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter,
                                 description='Lisataan LUT taulukkoon antureita')
parser.add_argument('--data_path', type=dir_path,
                    default=r'C:\Users\Public\Documents\Ultrasound_IQ_analysis\QA_analysis\Extra_data\Testi\140722-ilmakuvat',
                    help='hakemisto joka sisaltaa listattavat dicom tiedostot')
parser.add_argument('--excel_writer_path', type=str,
                    default=r'C:\Users\Public\Documents\Ultrasound_IQ_analysis\QA_analysis\LUT.xls',
                    help='Hakemistopolku excel tiedostoon johon tiedot lisataan automaattisesti')

args = parser.parse_args()
excel_writer = args.excel_writer_path

# Luettele kaikki tiedostot ja kansiot polusta
filenames = glob(args.data_path + '/**/*', recursive=True)
# import pdb; pdb.set_trace()

for filename in filenames:  # Tama looppi kay dcm tiedostot lapi ja lisaa metatiedot taulukkoon
    # Ohita kansiot
    if os.path.isdir(filename):
        continue

    data = pydicom.dcmread(os.path.join(args.data_path, filename))
    dct_params = extract_parameters(data, get_name=True)

    df1 = pd.DataFrame(data=dct_params)
    try:
        df = pd.read_excel(excel_writer)
    except:
        df = pd.DataFrame({})
    try:
        df.drop(['Unnamed: 0'], axis=1, inplace=True)
    except:
        None

    frames = [df, df1]
    df_total = pd.concat(frames)
    df_total.to_excel(excel_writer, engine='openpyxl')
