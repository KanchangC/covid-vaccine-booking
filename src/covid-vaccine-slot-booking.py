import argparse
import jwt
from types import SimpleNamespace
from utils import *
from useragent import get_user_agent


def is_token_valid(token):
    payload = jwt.decode(token, options={"verify_signature": False})
    remaining_seconds = payload['exp'] - int(time.time())
    if remaining_seconds <= 1 * 30:  # 30 secs early before expiry for clock issues
        return False
    if remaining_seconds <= 60:
        print("Token is about to expire in next 1 min ...")
    return True


def multi_cycle_book(request_header, token, mobile, otp_pref, base_request_header, otp_validation_header, info,
                     beneficiary_dtls,
                     collected_details):
    while True:  # infinite-loop
        # create new request_header
        request_header = copy.deepcopy(base_request_header)
        request_header["Authorization"] = f"Bearer {token}"

        # call function to check and book slots
        try:
            token_valid = is_token_valid(token)

            # token is invalid ?
            # If yes, generate new one
            if not token_valid:
                print('Token is INVALID.')
                token = None
                while token is None:
                    if otp_pref == "n":
                        try:
                            token = generate_token_OTP(mobile, base_request_header, otp_validation_header)
                        except Exception as e:
                            print(str(e))
                            print('OTP Retrying in 5 seconds')
                            time.sleep(5)
                    elif otp_pref == "y":
                        token = generate_token_OTP_manual(mobile, base_request_header, otp_validation_header)
            check_and_book(request_header, beneficiary_dtls, info.location_dtls, info.search_option,
                           min_slots=info.minimum_slots,
                           ref_freq=info.refresh_freq,
                           auto_book=info.auto_book,
                           start_date=info.start_date,
                           vaccine_type=info.vaccine_type,
                           fee_type=info.fee_type,
                           mobile=mobile,
                           captcha_automation=info.captcha_automation,
                           captcha_api_choice=info.captcha_api_choice,
                           captcha_automation_api_key=info.captcha_automation_api_key,
                           dose_num=get_dose_num(collected_details),
                           excluded_pincodes=info.excluded_pincodes,
                           reschedule_inp=info.reschedule_inp
                           )
        except Exception as e:
            print(str(e))
            print('Retrying in 5 seconds')
            time.sleep(5)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--token', help='Pass token directly')
    args = parser.parse_args()

    filename = 'vaccine-booking-details-'
    mobile = None

    print('Running Script')
    beep(500, 150)
    try:
        base_request_header = {
            'User-Agent': get_user_agent()
            , 'origin': 'https://selfregistration.cowin.gov.in'
            , 'referer': 'https://selfregistration.cowin.gov.in/'
        }
        otp_validation_header = {
            'User-Agent': get_user_agent()
            , 'origin': 'https://selfregistration.cowin.gov.in'
            , 'sec-fetch-site': 'cross-site'
            , 'sec-fetch-mode': 'cors'
            , 'sec-fetch-dest': 'empty'
            , 'referer': 'https://selfregistration.cowin.gov.in/',
        }

        common_header = {
            'User-Agent': get_user_agent()
            , 'content-type': 'application/json'
            , 'origin': 'https://selfregistration.cowin.gov.in/'
            , 'sec-fetch-site': 'cross-site'
            , 'sec-fetch-mode': 'cors'
            , 'sec-fetch-dest': 'empty'
            , 'referer': 'https://selfregistration.cowin.gov.in/',
        }

        token = None
        if args.token:
            token = args.token
        else:
            mobile = input("Enter the registered mobile number: ")
            filename = filename + mobile + ".json"
            otp_pref = input(
                "\nDo you want to enter OTP manually, instead of auto-read? \nRemember selecting n would require some setup described in README (y/n Default n): ")
            otp_pref = otp_pref if otp_pref else "n"
            while token is None:
                if otp_pref.lower() == "n":
                    try:
                        token = generate_token_OTP(mobile, base_request_header, otp_validation_header)
                    except Exception as e:
                        print(str(e))
                        print('OTP Retrying in 5 seconds')
                        time.sleep(5)
                elif otp_pref.lower() == "y":
                    token = generate_token_OTP_manual(mobile, base_request_header, otp_validation_header)

        request_header = copy.deepcopy(common_header)
        request_header["Authorization"] = f"Bearer {token}"
        if os.path.exists(filename):
            print("\n=================================== Note ===================================\n")
            print(f"Info from perhaps a previous run already exists in {filename} in this directory.")
            print(
                f"IMPORTANT: If this is your first time running this version of the application, DO NOT USE THE FILE!")
            try_file = input("Would you like to see the details and confirm to proceed? (y/n Default y): ")
            try_file = try_file if try_file else 'y'

            if try_file.lower() == 'y':
                collected_details = get_saved_user_info(filename)
                print("\n================================= Info =================================\n")
                display_info_dict(collected_details)

                file_acceptable = input("\nProceed with above info? (y/n Default n): ")
                file_acceptable = file_acceptable if file_acceptable else 'n'
                if file_acceptable.lower() != 'y':
                    collected_details = collect_user_details(request_header)
                    save_user_info(filename, collected_details)

            else:
                collected_details = collect_user_details(request_header)
                save_user_info(filename, collected_details)

        else:
            collected_details = collect_user_details(request_header)
            save_user_info(filename, collected_details)
            confirm_and_proceed(collected_details)

        info = SimpleNamespace(**collected_details)

        if info.minimum_slots != len(info.beneficiary_dtls):
            for beneficiary in info.beneficiary_dtls:
                multi_cycle_book(request_header, token, mobile, otp_pref, base_request_header, otp_validation_header,
                                 info, beneficiary, collected_details)
            print('\n press any key twice to exit \n')
            os.system("pause")
            os.system("pause")
            sys.exit()
        else:
            multi_cycle_book(request_header, token, mobile, otp_pref, base_request_header, otp_validation_header,
                             info, info.beneficiary_dtls, collected_details)

            print('\n press any key twice to exit \n')
            os.system("pause")
            os.system("pause")
            sys.exit()
    except Exception as e:
        print(str(e))
        print('Exiting Script')
        os.system("pause")


if __name__ == '__main__':
    main()
