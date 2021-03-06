import numpy as np
import subprocess as sub
import time
import os
import glob
import sys
import shutil


def time_check_call(cmd_str, shell=True, debug=False):
    tstart = time.time()
    retval = 0
    try:
        if debug:
            print cmd_str
        else:
            retval = sub.check_call(cmd_str, shell=shell)
    except sub.CalledProcessError:
        retval = 1
        print("cmd failed: %s" %cmd_str)
    dt = tstart - time.time()
    return dt, retval


def param_string_from_dict(pdict):
    pstr = ""
    for kk, vv in pdict.items():
        pstr += "-%s %s " %(kk, str(vv))
    return pstr


def dedisperse_beam(fitsfile, out_dir, out_name, rfi_mask=None, pdict={}, debug=False):
    err_val = 0

    param_str = param_string_from_dict(pdict)
    cmd_str = "prepsubband -o %s/%s " %(out_dir, out_name)
    cmd_str += param_str

    # if rfi_mask exists, add it to command string
    if rfi_mask is not None and os.path.isfile(rfi_mask):
        cmd_str += "-mask %s " %rfi_mask
    else: pass
    
    # if fits file exists, add to command string
    if os.path.isfile(fitsfile):
        cmd_str += fitsfile
    else:
        err_val += 1
        
    # if no errors, try running function
    if err_val == 0:
        dt, retval = time_check_call(cmd_str, shell=True, debug=debug)
        err_val += retval
    else:
        dt = 0

    return dt, err_val


def dedisperse_beam2(fitsfile, out_dir, out_name, rfi_mask=None, pdict={}, debug=False):
    """
    This version writes the dat files to a local scratch directory, 
    then moves them to the output directory.  This is just a work-around 
    to avoid overly long names (ie, the whole path) in the inf files
    """
    err_val = 0

    param_str = param_string_from_dict(pdict)
    cmd_str = "prepsubband -o %s " %(out_name)
    cmd_str += param_str

    # if rfi_mask exists, add it to command string
    print rfi_mask
    if rfi_mask is not None and os.path.isfile(rfi_mask):
        cmd_str += "-mask %s " %rfi_mask
        print "Using RFI mask: %s" %rfi_mask
        sys.stdout.flush()
    else:
        print "No RFI mask!!!"
        sys.stdout.flush()
    
    # if fits file exists, add to command string
    if os.path.isfile(fitsfile):
        cmd_str += fitsfile
        print cmd_str
    else:
        err_val += 1
        
    # if no errors, try running function
    if err_val == 0:
        dt, retval = time_check_call(cmd_str, shell=True, debug=debug)
        err_val += retval
    else:
        dt = 0

    # Now move the files to the output directory
    dat_files = glob.glob("%s*dat" %out_name)
    inf_files = glob.glob("%s*inf" %out_name)

    print(dat_files)
    print(inf_files)

    for ii in xrange(len(dat_files)):
        shutil.move(dat_files[ii], out_dir)
        shutil.move(inf_files[ii], out_dir)

    return dt, err_val


def run_single_pulse_search(dat_files, pdict={}, debug=False):
    err_val = 0
    
    param_str = param_string_from_dict(pdict)
    
    # check that data files have been created
    file_err = [ not (os.path.isfile(dat)) for dat in dat_files ]
    if np.any(file_err):
        err_val += 1
        print("Not all files exist!")
        sys.stdout.flush()
    else: pass

    # if files are good, build cmd string and run 
    cmd_str = "single_pulse_search.py %s %s" %(param_str, ' '.join(dat_files))
    print(cmd_str)

    if err_val == 0:
        dt, retval = time_check_call(cmd_str, shell=True, debug=debug)
        err_val += retval
    else:
        dt = 0
    
    return dt, err_val


def dedisperse_multi_beam(beam_list, fits_dir, fits_base, 
                          beams_dir, mask_file, ddm_pars = {}, debug=False):
    dt_list  = np.zeros(len(beam_list))
    err_list = np.zeros(len(beam_list))

    # Make sure beams_dir exists
    if not os.path.exists(beams_dir):
        print("%s does not exist!  Exiting..." %beams_dir)
        return
    else: pass

    for ii, bnum in enumerate(beam_list):
        fitsfile = "%s/%s_beam%04d.fits" %(fits_dir, fits_base, bnum)

        # check if fitsfile exists
        if not os.path.isfile(fitsfile):
            print("file not found: %s" %fitsfile)
            continue
        
        # Check to see if output dir exists, if not make it
        out_dir = "%s/beam%04d" %(beams_dir, bnum)
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
        else: pass

        out_name = "beam%04d" %bnum
        
        dt, errcode = dedisperse_beam2(fitsfile, out_dir, out_name,
                                      rfi_mask=mask_file, pdict=ddm_pars,
                                      debug=debug)

        dt_list[ii] = dt
        err_list[ii] = errcode

    return dt_list, err_list



def run_single_pulse_multi_beam(beam_list, beams_dir, sp_pars={}, debug=False):
    dt_list  = np.zeros(len(beam_list))
    err_list = np.zeros(len(beam_list))
    
    # Make sure beams_dir exists
    if not os.path.exists(beams_dir):
        print("%s does not exist!  Exiting..." %beams_dir)
        return
    else: pass

    for ii, bnum in enumerate(beam_list):
        # Check to see if dat dir exists 
        dat_dir = "%s/beam%04d" %(beams_dir, bnum)
        if not os.path.exists(dat_dir):
            print("dat dir not found: %s" %dat_dir)
            continue
        else: pass

        dat_base = "beam%04d" %bnum
        dat_files = glob.glob("%s/%s*dat" %(dat_dir, dat_base))
        dat_files.sort()

        dt, errcode = run_single_pulse_search(dat_files, pdict=sp_pars, debug=debug)
        
        dt_list[ii] = dt
        err_list[ii] = errcode

    return dt_list, err_list


def combine_sp_files(sp_files, outfile):
    sp_files.sort()
    fout = open(outfile, 'w')
    for ii, spfile in enumerate(sp_files):
        jj = 0
        for line in file(spfile):
            if (ii==0 and jj==0) or (jj>0):
                fout.write(line)
            else:
                pass
            jj += 1
    fout.close()
    return


def combine_sp_files_multi(beam_list, beams_dir):
    # Make sure beams_dir exists
    if not os.path.exists(beams_dir):
        print("%s does not exist!  Exiting..." %beams_dir)
        return
    else: pass

    for ii, bnum in enumerate(beam_list):
        # Check to see if dat dir exists 
        dat_dir = "%s/beam%04d" %(beams_dir, bnum)
        if not os.path.exists(dat_dir):
            print("dat dir not found: %s" %dat_dir)
            continue
        else: pass

        sp_base = "beam%04d" %bnum
        sp_files = glob.glob("%s/%s*singlepulse" %(dat_dir, sp_base))
        sp_files.sort()

        outfile = "%s/%s.cands" %(dat_dir, sp_base)
        combine_sp_files(sp_files, outfile)
    return




if __name__ == "__main__":

    do_dm = 1
    do_sp = 1

    fits_base = 'mjd57514_part1'
    beams = np.arange(0, 2000, dtype='int')
    
    #top_dir = '/lustre/aoc/projects/16A-459/beamforming/57511/test/processing'
    top_dir = '.'

    fits_dir  = '%s/psrfits' %top_dir
    beams_dir = '%s/search' %top_dir

    mask_dir = '%s/search/rfi_mask' %top_dir
    mask_file = '%s/%s_rfifind.mask' %(mask_dir, fits_base)

    ddm_pars_small = {'numdms' : 7,
                      'dmstep' : 3.0, 
                      'lodm'   : 548.0, 
                      'nsub'   : 32}

    ddm_pars_large = {'numdms' : 50,
                      'dmstep' : 10.0,
                      'lodm'   : 300.0,
                      'nsub'   : 32 }
#                      'nobary' : ''}
    
    #ddm_pars = ddm_pars_small
    ddm_pars = ddm_pars_large

    sp_pars = {'f' : '', 
               'm' : 0.02}

    # De-disperse
    tdm_start = time.time()
    if do_dm:
        dts_dm, errs_dm = dedisperse_multi_beam(beams, fits_dir, fits_base,
                                                beams_dir, mask_file, 
                                                ddm_pars=ddm_pars, debug=False)
    tdm = time.time() - tdm_start

    # Single Pulse Search
    tsp_start = time.time()
    if do_sp:
        tsp_start = time.time()
        dts_sp, errs_sp = run_single_pulse_multi_beam(beams, beams_dir, 
                                                      sp_pars=sp_pars, debug=False)
        combine_sp_files_multi(beams, beams_dir)
        
    tsp = time.time() - tsp_start
    

    print("Dedispersion took %.1f min" %(tdm / 60.0))
    print("SP searching took %.1f min" %(tsp / 60.0))
        
