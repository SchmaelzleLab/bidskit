#!/usr/bin/env python3
"""
Convert flat DICOM file set into a BIDS-compliant Nifti structure

Usage
----
dcm2bids.py -i <DICOM Directory> -o <BIDS Directory Root>

Example
----
% dcm2bids.py -i DICOM -o Experiment

Authors
----
Mike Tyszka, Caltech Brain Imaging Center

Dates
----
2016-08-03 JMT From scratch

MIT License

Copyright (c) 2016 Mike Tyszka

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

__version__ = '0.1.0'

import os
import sys
import argparse
import subprocess
import shutil
import json


def main():

    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Convert DICOM files to BIDS-compliant Nifty structure')
    parser.add_argument('-i','--indir', required=True, help='Input directory containing flat DICOM images')
    parser.add_argument('-o','--outdir', required=True, help='Output BIDS directory root')

    # Parse command line arguments
    args = parser.parse_args()

    dcm_dir = args.indir
    bids_dir = args.outdir

    print('Converting DICOM images from %s' % dcm_dir)

    # Safe create output directory
    subprocess.call(['rm', '-rf', bids_dir])
    subprocess.call(['mkdir', '-p', bids_dir])

    # Run dcm2niix conversion from DICOM into BIDS directory
    subprocess.call(['dcm2niix', '-b', 'y', '-o', bids_dir, dcm_dir])

    # Load BIDS directory listing
    dlist = os.listdir(bids_dir)

    # Get list of unique subjects by name from file list
    sid_list = get_unique_subjects(dlist)

    # Create participant CSV file in BIDS directory
    parts_csv = os.path.join(bids_dir, 'participants.csv')
    parts_fd = open(parts_csv, 'w')
    parts_fd.write('participant_id, sex, age\n')

    # Create template JSON dataset description
    datadesc_json = os.path.join(bids_dir, 'dataset_description.json')
    dd = dict({'BIDSVersion': "1.0.0",
               'License': "This data is made available under the Creative Commons BY-SA 4.0 International License.",
               'Name': "The dataset name goes here",
               'ReferencesAndLinks':"References and links for this dataset go here"})

    with open(datadesc_json, 'w') as fd:
        json.dump(dd, fd, indent=4, separators=(',',':'))

    # Loop over all subjects
    for sid in sid_list:

        print('Processing subject ' + sid)

        # Add line to participants CSV file
        parts_fd.write(sid + ', MF, 0\n')

        # Create subject directory
        sid_prefix = 'sub-' + sid
        sid_dir = os.path.join(bids_dir, sid_prefix)

        print('Creating directory for ' + sid)
        subprocess.call(['mkdir', '-p', sid_dir])

        # Subject subdirectory names
        anat_dir = os.path.join(sid_dir, 'anat')
        func_dir = os.path.join(sid_dir, 'func')
        fmap_dir = os.path.join(sid_dir, 'fmap')

        # Create subject subdirs
        subprocess.call(['mkdir', '-p', anat_dir])
        subprocess.call(['mkdir', '-p', func_dir])
        subprocess.call(['mkdir', '-p', fmap_dir])

        # Loop over all files for this SID
        for fname in os.listdir(bids_dir):

            fstub = strip_extensions(fname)

            if fstub.startswith(sid_prefix):

                seq = bids_get_seq(fstub)
                acq = bids_get_acq(fstub)

                if seq.startswith('T1') or seq.startswith('T2') or seq.startswith('FLASH'):
                    print('Moving %s to %s' % (fname, anat_dir))
                    shutil.move(os.path.join(bids_dir, fname), os.path.join(anat_dir, fname))

                if seq.startswith('bold'):
                    print('Moving %s to %s' % (fname, func_dir))
                    shutil.move(os.path.join(bids_dir, fname), os.path.join(func_dir, fname))

                if acq.startswith('fmap'):
                    print('Moving %s to %s' % (fname, fmap_dir))
                    shutil.move(os.path.join(bids_dir, fname), os.path.join(fmap_dir, fname))


    # Clean up
    parts_fd.close()

    # Clean exit
    sys.exit(0)


def get_unique_subjects(dlist):

    # Create an empty set for subject names
    sid_set = set()

    for fname in dlist:
        sid_set.add(bids_get_sid(fname))

    # Convert set to list
    sid_list = list(sid_set)

    return sid_list


def bids_get_sid(fname):
    d = bids_parse_filename(fname)
    return d.get('sub','Unknown')


def bids_get_seq(fname):
    d = bids_parse_filename(fname)
    return d.get('seq','Unknown')


def bids_get_acq(fname):
    d = bids_parse_filename(fname)
    return d.get('acq','Unknown')


def bids_parse_filename(fname):

    # Init dictionary
    d = dict()

    # Isolate each key-value pair
    for keyval in fname.split('_'):

        # Handle final sequence suffix in filename (_bold, _epi, etc)
        if '-' in keyval:
            key, val = keyval.split('-')
        else:
            key, val = 'seq', keyval

        d[key] = val

    # Return filled dictionary
    return d


def strip_extensions(fname):
    fstub, fext = os.path.splitext(fname)
    if fext == '.gz':
        fstub, fext = os.path.splitext(fstub)
    return fstub


# This is the standard boilerplate that calls the main() function.
if __name__ == '__main__':
    main()