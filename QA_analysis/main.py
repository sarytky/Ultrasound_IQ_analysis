from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
import os
import pickle
import argparse
import time
import yaml
from datetime import date
from utils.utils import check_if_US_data, save_dct, compare_results, line_prepender1, line_prepender2, \
    line_prepender_list
import utils.UA_QA_analysis as QA


def dir_path(string):
    if os.path.isdir(string):
        return string
    else:
        raise NotADirectoryError(string)


def on_created(event):
    # Use a global variable for arguments to allow updating them outside the function
    global args

    print(f"File: {event.src_path} added to directory.")

    if args.check_dicom_extension and not event.src_path.endswith('.dcm'):  # Assume dicom extension (check input args)
        print('Not a DICOM file.')
        return None
    elif args.check_test_id and not check_if_US_data(event.src_path, args.id2cmp):  # Check for test patient ID
        print('File not in the list of allowed test patients.')
        return None

    print("Run analysis...")
    res = QA.MAIN_US_analysis(event.src_path, path_LUT_table=args.path_LUT_table)  # Returns a dictionary

    # Rakenna tiedostosijainnit tuloksia varten:
    directory_device = str(res['name'])
    path = os.path.join(args.save_path, directory_device)
    try:
        os.mkdir(path)
    except OSError:
        print("Transducers analysed previously from this device")

    flag_analysed_before = False  # init

    directory_transducer = str(res['transducer_name'])
    path = os.path.join(path, directory_transducer)
    try:
        os.mkdir(path)
    except OSError as error:
        print(error)
        print("Transducer analysed previously")
        flag_analysed_before = True
        path_vo_data = path + '/1'  # vastaanottomittaus on eka.

    path_old = path
    uniq = 1
    while os.path.exists(path):  # etsii ensimmäisen seuraavaksi vapaan luvun 1 lähtien
        path = path_old + '/%d' % uniq
        uniq += 1

    # --- Vertaa ensimmäiseen mittaukseen ---
    if flag_analysed_before:
        with open(path_vo_data, 'rb') as handle:
            res_vo_dct = pickle.load(handle)

        res_cmp, alert_flag = compare_results(res, res_vo_dct, threshold=args.TH)
    # ----------------------------------------

    # ---- Make log file ---- :
    today = date.today()
    d1 = today.strftime("%d/%m/%Y")
    text_list = d1
    if flag_analysed_before:  # eri kirjaukset jos on analysoitu aikaisemmin
        flag = False
        for v in alert_flag.items():
            if v:
                flag = True

        if not flag:
            # import pdb; pdb.set_trace()
            text_list = 'Analysoitu laite:' + res['name'] + 'Anturi: ' + res['transducer_name']
            text_list = d1 + ' OK ' + text_list
            line_prepender1(args.log_filename, text_list)
        else:
            text = text_list + ' Analysoitu laite: ' + str(res['name']) + ' anturi: ' + str(
                res['transducer_name']), + '\n'
            text_list = [text]
            # --- eroavaisuus notifikaatio ---
            for k in alert_flag.keys():
                if k == 'U_low':
                    list1 = alert_flag[k]
                    list2 = res_cmp[k]
                    txt_list = []
                    for i in range(len(list1)):
                        if list1[i]:
                            text2 = 'Eroavaisuus löytyi: ' + k + ' i' + ': ' + str(
                                list2[i]) + ' (suhteellinen virhe)\n'
                            txt_list.append(text2)
                            text_list.append(text2)
                        else:
                            if alert_flag[k]:
                                text2 = 'Eroavaisuus löytyi: ' + k + ': ' + str(
                                    res_cmp[k]) + ' (suhteellinen virhe)\n'
                                text_list.append(text2)

            if isinstance(text_list, list):
                txt = text_list.pop(0)
                line_prepender_list(args.log_filename, text_list)
                line_prepender2(args.log_filename, f'{d1} {txt}')
            else:
                line_prepender1(args.log_filename, f'{d1} {text_list}')

    else:

        text_list = 'Analysoitu laite:' + res['name'] + ' Anturi: ' + res['transducer_name']
        text_list = d1 + ' OK ' + text_list
        line_prepender1(args.log_filename, text_list)

    # ---------------------------------

    # ------------- Tallennus -------- :
    save_dct(res, path)
    print('Analyysi valmis!')
    # ---------------------------------


def on_deleted(event):
    print(f"{event.src_path} is deleted.")


def on_modified(event):
    print(f"{event.src_path} file is modified.")


def on_moved(event):
    print(f"Moved from {event.src_path} to {event.dest_path}.")


if __name__ == "__main__":

    # ---- Initialization: ----

    parser = argparse.ArgumentParser()
    parser.add_argument('--settings_path', type=str,
                        default=os.path.join(os.getcwd(), 'Settings.yaml'))
    parser.add_argument('--log_filename', type=str, default='log_file.txt')
    parser.add_argument('--data_path', type=str)
    parser.add_argument('--check_dicom_extension', type=bool, defaul=False, help='Require .dcm-extension')
    parser.add_argument('--check_test_id', type=bool, defaul=False, help='Require specific patient IDs for US images')

    args = parser.parse_args()

    # Get the values from the settings.yaml file
    with open(args.settings_path) as a_yaml_file:
        dct = yaml.load(a_yaml_file, Loader=yaml.FullLoader)
        args.data_path = dct['data_path']
        args.save_path = dct['save_path']
        args.id2cmp = dct['id_us_analysis']
        args.path_LUT_table = dct['path_LUT_table']
        args.TH = dct['threshold_val']

    print('Analysis software started')
    print('Close using ctrl+c by closing the window')

    # %% --- Watch dog ---
    # Define Watchdog event handler
    my_event_handler = PatternMatchingEventHandler(patterns="*",
                                                   ignore_patterns="",
                                                   ignore_directories=True,
                                                   case_sensitive=True)
    my_event_handler.on_created = on_created
    my_event_handler.on_deleted = on_deleted
    my_event_handler.on_modified = on_modified
    my_event_handler.on_moved = on_moved

    # Watchdog observer to monitor data folder
    my_observer = Observer()
    my_observer.schedule(my_event_handler, args.data_path, recursive=True)
    my_observer.start()

    # Update settings every hour
    try:
        while True:
            time.sleep(3600)
            with open(args.settings_path) as a_yaml_file:
                dct = yaml.load(a_yaml_file, Loader=yaml.FullLoader)
                args.data_path = dct['data_path']
                args.save_path = dct['save_path']
                args.id2cmp = dct['id_us_analysis']
                args.path_LUT_table = dct['path_LUT_table']
                args.TH = dct['threshold_val']
    except KeyboardInterrupt:
        my_observer.stop()
        my_observer.join()
