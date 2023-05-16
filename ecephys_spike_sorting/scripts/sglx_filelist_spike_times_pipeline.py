import os
import numpy as np
from helpers import SpikeGLX_utils
from helpers import run_one_probe
from create_input_json import createInputJson

def spike_times_npy_to_sec(sp_fullPath, sample_rate, bNPY):
    # convert spike_times.npy to text of times in sec
    # return path to the new file. Can take sample_rate as a
    # parameter, or set to 0 to read from param file

    # get file name and create path to new file
    sp_path, sp_fileName = os.path.split(sp_fullPath)
    baseName, bExt = os.path.splitext(sp_fileName)
    if bNPY:
        new_fileName = baseName + '_sec.npy'
    else:
        new_fileName = baseName + '_sec.txt'
        
    new_fullPath = os.path.join(sp_path, new_fileName)

    # load spike_times.npy; returns numpy array (Nspike,) as uint64
    spike_times = np.load(sp_fullPath)

    if sample_rate == 0:
        # get sample rate from params.py file, assuming sp_path is a full set
        # of phy output
        with open(os.path.join(sp_path, 'params.py'), 'r') as f:
            currLine = f.readline()
            while currLine != '':  # The EOF char is an empty string
                if 'sample_rate' in currLine:
                    sample_rate = float(currLine.split('=')[1])
                    print(f'sample_rate read from params.py: {sample_rate:.10f}')
                currLine = f.readline()

            if sample_rate == 0:
                print('failed to read in sample rate\n')
                sample_rate = 30000

    spike_times_sec = spike_times/sample_rate   # spike_times_sec dtype = float

    if bNPY:
        # write out npy file
        np.save(new_fullPath, spike_times_sec)
    else:
        # write out single column text file
        nSpike = len(spike_times_sec)
        with open(new_fullPath, 'w') as outfile:
            for i in range(0, nSpike-1):
                outfile.write(f'{spike_times_sec[i]:.6f}\n')
            outfile.write(f'{spike_times_sec[nSpike-1]:.6f}')

    return new_fullPath


# script to run sorting and postprocessing moduels on a list of recordings
# the SpikeGLX metadata must be in the directory with the binary.
# output is directed to a newly made directory next to the input binary.


# -------------------------------
# -------------------------------
# User input -- Edit this section
# -------------------------------
# -------------------------------
# Full path to log file
# If this file exists, new run data is appended to it
logFullPath = r'D:\SC048_out\catgt_SC048_122920_ex_g0\pipeline_log.csv'

# brain region specific params
# can add a new brain region by adding the key and value for each param
# can add new parameters -- any that are taken by create_input_json --
# by adding a new dictionary with entries for each region and setting the 
# according to the new dictionary in the loop to that created json files.

refPerMS_dict = {'default': 2.0, 'cortex': 2.0, 'medulla': 1.5, 'thalamus': 1.0}

# threhold values appropriate for KS2, KS2.5
ksTh_dict = {'default':'[10,4]', 'cortex':'[10,4]', 'medulla':'[10,4]', 'thalamus':'[10,4]'}
# threshold values appropriate for KS3.0
# ksTh_dict = {'default':'[9,9]', 'cortex':'[9,9]', 'medulla':'[9,9]', 'thalamus':'[9,9]'}

# -----------
# Input data
# -----------


# Raw data directory = npx_directory
# run_specs = name, gate, trigger and probes to process
npx_directory = r'D:\SC048_out\catgt_SC048_122920_ex_g0'

# for each recording, specfiy a full path the the binary and a brain region

recording_specs = [									
				[r'D:\SC048_out\catgt_SC048_122920_ex_g0\SC048_122920_ex_g0_tcat.imec0.ap.bin', ['default'] ]

]



# ----------------------
# KS2 or KS25 parameters
# ----------------------
# parameters that will be constant for all recordings
# Template ekmplate radius and whitening, which are specified in um, will be 
# translated into sites using the probe geometry.
ks_remDup = 0
ks_saveRez = 1
ks_copy_fproc = 0
ks_templateRadius_um = 163
ks_whiteningRadius_um = 163
ks_minfr_goodchannels = 0.1

# If running KS20_for_preprocessed_data:
# (https://github.com/jenniferColonell/KS20_for_preprocessed_data)
# can skip filtering with the doFilter parameter.
# Useful for speed when data has been filtered with CatGT.
# This parameter is not implemented in standard versions of kilosort.
ks_doFilter = 0

# ----------------------
# C_Waves snr radius, um
# ----------------------
c_Waves_snr_um = 160



# ---------------
# Modules List
# ---------------
# List of modules to run per probe; CatGT and TPrime are called once for each run.
modules = [
			'kilosort_helper',
            'kilosort_postprocessing',
            #'noise_templates',
            #'mean_waveforms',
            #'quality_metrics'
			]

json_directory = r'C:\Users\colonellj\Documents\ecephys_anaconda\json_files'

# -----------------------
# -----------------------
# End of user input
# -----------------------
# -----------------------


# delete existing C_waves.log
try:
    os.remove('C_Waves.log')
except OSError:
    pass


# first loop over recording specs to create output directories and
#  make json file for each

# initialize lists    
module_input_json = []
module_output_json = []
session_id = []
data_directory = []
spike_npy_paths = []
 
for i, spec in enumerate(recording_specs):
    
    path = spec[0]
    npx_directory = os.path.dirname(path)
    fname, fextension = os.path.splitext(path)
    input_meta_fullpath = os.path.join(npx_directory, (fname + '.meta'))
    print(input_meta_fullpath)
    binName = os.path.basename(path)
    baseName = SpikeGLX_utils.ParseTcatName(binName)
    prbStr = SpikeGLX_utils.GetProbeStr(binName)   # returns empty string for 3A


    # Create output directory
    kilosort_output_parent = os.path.join(npx_directory, baseName)
    
    if not os.path.exists(kilosort_output_parent):
        os.mkdir(kilosort_output_parent)
        
        
    # output subdirectory
    outputName = 'imec' + prbStr + '_ks2'
    
    kilosort_output_dir = os.path.join(kilosort_output_parent, outputName)
    spike_npy_paths.append(os.path.join(kilosort_output_dir, 'spike_times.npy'))
    
    session_id.append(baseName) 
    
    module_input_json.append(os.path.join(json_directory, session_id[i] + '-input.json'))
    
    data_directory.append(npx_directory)
    continuous_file = os.path.join(data_directory[i], binName)
 

    # kilosort_postprocessing and noise_templates moduules alter the files
    # that are input to phy. If using these modules, keep a copy of the
    # original phy output
    if ('kilosort_postprocessing' in modules) or('noise_templates' in modules):
        ks_make_copy = True
    else:
        ks_make_copy = False

    
    # get region specific parameters
    ks_Th = ksTh_dict.get(spec[1][0])
    refPerMS = refPerMS_dict.get(spec[1][0])

    info = createInputJson(module_input_json[i], npx_directory=npx_directory,
                                   continuous_file = continuous_file,
                                   spikeGLX_data = True,
                                   input_meta_path = input_meta_fullpath,
                                   kilosort_output_directory = kilosort_output_dir,
                                   ks_make_copy = ks_make_copy,
                                   noise_template_use_rf = False,
                                   catGT_run_name = session_id[i],  
                                   ks_remDup = ks_remDup,                   
                                   ks_finalSplits = 1,
                                   ks_labelGood = 1,
                                   ks_saveRez = ks_saveRez,
                                   ks_copy_fproc = ks_copy_fproc,
                                   ks_minfr_goodchannels = ks_minfr_goodchannels,                  
                                   ks_whiteningRadius_um = ks_whiteningRadius_um,
                                   ks_doFilter = ks_doFilter,
                                   ks_Th = ks_Th,
                                   ks_CSBseed = 1,
                                   ks_LTseed = 1,
                                   ks_templateRadius_um = ks_templateRadius_um,
                                   extracted_data_directory = npx_directory,
                                   c_Waves_snr_um = c_Waves_snr_um,                               
                                   qm_isi_thresh = refPerMS/1000
                                   )   

    # copy json file to data directory as record of the input parameters 
       
        
# loop over files again for processing. 
# not running CatGT; set params accorindly
run_CatGT = False
catGT_input_json = ''
catGT_output_json = ''

for i, spec in enumerate(recording_specs):
       
    run_one_probe.runOne( session_id[i],
             json_directory,
             data_directory[i],
             run_CatGT,
             catGT_input_json,
             catGT_output_json,
             modules,
             module_input_json[i],
             logFullPath )
    
    # run conversion to seconds for spike_times.npy for this recording
    # sample rate is read from the params.py file
    bNPY = 1 # set to 1 to output npy files of time in seconds (recommended)k zero for text
    spike_times_npy_to_sec(spike_npy_paths[i], 0, bNPY)
                 
        
