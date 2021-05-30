import json
import copy
import datetime
import random
import requests
import sys
import tabulate
import time
from inputimeout import TimeoutOccurred
from collections import Counter
from hashlib import sha256

from captcha import captcha_builder_manual, captcha_builder_auto, captcha_builder_api

BOOKING_URL = "https://cdn-api.co-vin.in/api/v2/appointment/schedule"
BENEFICIARIES_URL = "https://cdn-api.co-vin.in/api/v2/appointment/beneficiaries"
CALENDAR_URL_DISTRICT = "https://cdn-api.co-vin.in/api/v2/appointment/sessions/calendarByDistrict?district_id={0}&date={1}"
CALENDAR_URL_PINCODE = "https://cdn-api.co-vin.in/api/v2/appointment/sessions/calendarByPin?pincode={0}&date={1}"
CAPTCHA_URL = "https://cdn-api.co-vin.in/api/v2/auth/getRecaptcha"
OTP_PUBLIC_URL = "https://cdn-api.co-vin.in/api/v2/auth/public/generateOTP"
OTP_PRO_URL = "https://cdn-api.co-vin.in/api/v2/auth/generateMobileOTP"
RESCHEDULE_URL = "https://cdn-api.co-vin.in/api/v2/appointment/reschedule"
CANCEL_URL = "https://cdn-api.co-vin.in/api/v2/appointment/cancel"
WARNING_BEEP_DURATION = (1000, 5000)

try:
    import winsound

except ImportError:
    import os

    if sys.platform == "darwin":

        def beep(freq, duration):
            # brew install SoX --> install SOund eXchange universal sound sample translator on mac
            os.system(
                f"play -n synth {duration / 1000} sin {freq} >/dev/null 2>&1")
    else:
        def beep(freq, duration):
            # apt-get install beep  --> install beep package on linux distros before running
            os.system('beep -f %s -l %s' % (freq, duration))
else:
    def beep(freq, duration):
        winsound.Beep(freq, duration)


def book_appointment(request_header, details, mobile, generate_captcha_pref, api_key=None, captcha_api_choice=None):
    """
    This function
        1. Takes details in json format
        2. Attempts to book an appointment using the details
        3. Returns True or False depending on Token Validity
    """
    try:
        valid_captcha = True
        while valid_captcha:
            captcha = generate_captcha(request_header, generate_captcha_pref, api_key, captcha_api_choice)
            details["captcha"] = captcha

            print(
                "================================= ATTEMPTING BOOKING =================================================="
            )
            resp = requests.post(BOOKING_URL, headers=request_header, json=details)
            print(f"Booking Response Code: {resp.status_code}")
            print(f"Booking Response : {resp.text}")
            if resp.status_code == 401:
                print("TOKEN INVALID")
                return False
            elif resp.status_code == 200:
                beep(WARNING_BEEP_DURATION[0], WARNING_BEEP_DURATION[1])
                print(
                    "##############    BOOKED!  ############################    BOOKED!  ##############"
                )
                print(
                    "                        Hey, Hey, Hey! It's your lucky day!                       "
                )
                booked_appointment_id = resp.text
                booked_appointment_id = (booked_appointment_id[32:68])
                print(booked_appointment_id)
                response = requests.get(
                    "https://cdn-api.co-vin.in/api/v2/appointment/appointmentslip/download?appointment_id={}".format(
                        booked_appointment_id), headers=request_header)
                if response.status_code == 200:
                    filename = "appointment_slip" + booked_appointment_id
                    with open(filename, 'wb') as f:
                        f.write(response.content)

                #                print("\nPress any key thrice to exit program.")
                return 1000
            #                os.system("pause")
            #                os.system("pause")
            #                os.system("pause")
            #                sys.exit()

            elif resp.status_code == 409:
                print(f"Response: {resp.status_code} : {resp.text}")
                try:
                    data = resp.json()
                    # Response: 409 : {"errorCode":"APPOIN0040","error":"This vaccination center is completely booked for the selected date. Please try another date or vaccination center."}
                    if data.get("errorCode", '') == 'APPOIN0040':
                        time.sleep(2)
                        return 1
                except Exception as e:
                    print(str(e))
                return 2
            elif resp.status_code == 400:
                print(f"Response: {resp.status_code} : {resp.text}")
                # Response: 400 : {"errorCode":"APPOIN0044", "error":"Please enter valid security code"}
                pass
            elif resp.status_code >= 500:
                print(f"Response: {resp.status_code} : {resp.text}")
                # Server error at the time of high booking
                # Response: 500 : {"message":"Throughput exceeds the current capacity of your table or index.....","code":"ThrottlingException","statusCode":400,"retryable":true}
                pass
            else:
                print(f"Response: {resp.status_code} : {resp.text}")
                return True

    except Exception as e:
        print(str(e))
        beep(WARNING_BEEP_DURATION[0], WARNING_BEEP_DURATION[1])


def check_and_book(
        request_header, beneficiary_dtls, location_dtls, search_option, **kwargs
):
    """
    This function
        1. Checks the vaccination calendar for available slots,
        2. Lists all viable options,
        3. Takes user's choice of vaccination center and slot,
        4. Calls function to book appointment, and
        5. Returns True or False depending on Token Validity
    """
    slots_available = False
    try:
        min_age_booking = get_min_age(beneficiary_dtls)

        minimum_slots = kwargs["min_slots"]
        refresh_freq = kwargs["ref_freq"]
        auto_book = kwargs["auto_book"]
        start_date = kwargs["start_date"]
        vaccine_type = kwargs["vaccine_type"]
        fee_type = kwargs["fee_type"]
        mobile = kwargs["mobile"]
        captcha_automation = kwargs['captcha_automation']
        captcha_api_choice = kwargs['captcha_api_choice']
        captcha_automation_api_key = kwargs['captcha_automation_api_key']
        dose_num = kwargs['dose_num']
        excluded_pincodes = kwargs['excluded_pincodes'],
        reschedule_inp = kwargs['reschedule_inp']

        if isinstance(start_date, int) and start_date == 2:
            start_date = (
                    datetime.datetime.today() + datetime.timedelta(days=1)
            ).strftime("%d-%m-%Y")
        elif isinstance(start_date, int) and start_date == 1:
            start_date = datetime.datetime.today().strftime("%d-%m-%Y")
        else:
            pass

        if search_option == 2:
            options = check_calendar_by_district(
                request_header,
                vaccine_type,
                location_dtls,
                start_date,
                minimum_slots,
                min_age_booking,
                fee_type,
                dose_num,
                excluded_pincodes
            )
        else:
            options = check_calendar_by_pincode(
                request_header,
                vaccine_type,
                location_dtls,
                start_date,
                minimum_slots,
                min_age_booking,
                fee_type,
                dose_num
            )

        if isinstance(options, bool):
            return False

        options = sorted(
            options,
            key=lambda k: (
                k["district"].lower(),
                k["pincode"],
                k["name"].lower(),
                datetime.datetime.strptime(k["date"], "%d-%m-%Y"),
            ),
        )

        tmp_options = copy.deepcopy(options)
        if len(tmp_options) > 0:
            cleaned_options_for_display = []
            for item in tmp_options:
                item.pop("session_id", None)
                item.pop("center_id", None)
                cleaned_options_for_display.append(item)

            display_table(cleaned_options_for_display)
            slots_available = True

        else:
            for i in range(refresh_freq, 0, -1):
                msg = f"No viable options. Next update in {i} seconds.."
                print(msg, end="\r", flush=True)
                sys.stdout.flush()
                time.sleep(1)
            choice = "."

    except TimeoutOccurred:
        time.sleep(1)
        return True
    else:
        if not slots_available:
            return True
        else:
            # If we reached here then it means there is at-least one center having required doses.

            # sort options based on max available capacity of vaccine doses
            # highest available capacity of vaccine doses first for better chance of booking

            # ==> Caveat: if multiple folks are trying for same region like tier-I or tier-II cities then
            # choosing always first maximum available capacity may be a problem.
            # To solve this problem, we can use bucketization logic on top of available capacity
            #
            # Example:
            # meaning of pair is {center id, available capacity of vaccine doses at the center}
            # options = [{c1, 203}, {c2, 159}, {c3, 180}, {c4, 25}, {c5, 120}]
            #
            # Solution-1) Max available capacity wise ordering of options = [{c1, 203}, {c3, 180}, {c2, 159}, {c5, 120}, {c4, 25}]
            # Solution-2) Max available capacity with simple bucketization wise ordering of options = [{c1, 200}, {c3, 150}, {c2, 150}, {c5, 100}, {c4, 0}] when bucket size = 50
            # Solution-3) Max available capacity with simple bucketization & random seed wise ordering of options = [{c1, 211}, {c2, 180}, {c3, 160}, {c5, 123}, {c4, 15}] when bucket size = 50 + random seed
            #
            # Solution-3) is best as it also maximizing the chance of booking while considering max
            # at the same time it also adds flavour of randomization to handle concurrency.

            BUCKET_SIZE = 50
            options = sorted(
                options,
                key=lambda k: (BUCKET_SIZE * int(k.get('available', 0) / BUCKET_SIZE)) + random.randint(0,
                                                                                                        BUCKET_SIZE - 1),
                reverse=True)
            start_epoch = int(time.time())
            # if captcha automation is enabled then have less duration for stale information of centers & slots.
            MAX_ALLOWED_DURATION_OF_STALE_INFORMATION_IN_SECS = 1 * 30 if captcha_automation != 'n' else 1 * 5
            # Now try to look into all options unless it is not authentication related issue
            return_to_main_loop = 0

            for i in range(0, len(options)):
                option = options[i]
                all_slots_of_a_center = option.get("slots", [])
                ## break and go out of infinite while
                if return_to_main_loop > 0:
                    return False
                else:
                    if not all_slots_of_a_center:
                        continue
                    for selected_slot in all_slots_of_a_center:
                        current_epoch = int(time.time())
                        if current_epoch - start_epoch >= MAX_ALLOWED_DURATION_OF_STALE_INFORMATION_IN_SECS:
                            print(
                                "\n\ntried too many centers but still not able to book, look for current status of "
                                "centers....\n\n")
                            return True

                        try:
                            center_id = option["center_id"]
                            print(f"\n============> Trying Choice # {i} Center # {center_id}, Slot #{selected_slot}")

                            dose_num = 2 if [beneficiary["status"] for beneficiary in beneficiary_dtls][
                                                0] == "Partially Vaccinated" else 1
                            # reschedule

                            if reschedule_inp == "y":
                                new_req = {
                                    "appointment_id": beneficiary_dtls[0]['appointment_id'],
                                    "center_id": option["center_id"],
                                    "session_id": option["session_id"],
                                    "slot": selected_slot,
                                }
                                print(f"Booking with info: {new_req}")
                                booking_status = reschedule_appointment(request_header, new_req, mobile,
                                                                        captcha_automation,
                                                                        captcha_automation_api_key, captcha_api_choice)

                            else:
                                new_req = {
                                    "beneficiaries": [
                                        beneficiary["bref_id"] for beneficiary in beneficiary_dtls
                                    ],
                                    "dose": dose_num,
                                    "center_id": option["center_id"],
                                    "session_id": option["session_id"],
                                    "slot": selected_slot,
                                }
                                print(f"Booking with info: {new_req}")
                                booking_status = book_appointment(request_header, new_req, mobile, captcha_automation,
                                                                  captcha_automation_api_key, captcha_api_choice)
                            # is token error ? If yes then break the loop by returning immediately
                            if booking_status == 0:
                                return False
                            elif booking_status == 1000:
                                return_to_main_loop = return_to_main_loop + 1
                                break
                            else:
                                # try irrespective of booking status as it will be beneficial choice.
                                # try different center as slots are full for this center
                                # break the slots loop
                                print('Center is fully booked..Trying another...')
                                break
                        except IndexError:
                            print("============> Invalid Option!")
                            os.system("pause")
                            pass
                # tried all slots of all centers but still not able to book then look for current status of centers
                return True


# --------------this function was developed to filter centers by excluded pincode ---------------#
def get_all_pincodes(request_header, district_id, start_date, min_age):
    if start_date == 1:
        INP_DATE = datetime.datetime.today().strftime("%d-%m-%Y")
    else:
        INP_DATE = (datetime.datetime.today() + datetime.timedelta(days=1)).strftime("%d-%m-%Y")
    DIST_ID = district_id

    URL = \
        'https://cdn-api.co-vin.in/api/v2/appointment/sessions/public/calendarByDistrict?district_id={}&date={}'.format(
            DIST_ID,
            INP_DATE)
    response = requests.get(URL, headers=request_header)
    if response.status_code == 200:
        pincode_list = response.json()
        if "centers" in pincode_list:
            pincode_list = filter_centers_by_age(pincode_list, int(min_age))
            refined_pincodes = []
            if "centers" in pincode_list:
                for center in list(pincode_list["centers"]):
                    tmp = {"pincode": center["pincode"],
                           "name": center["name"],
                           "block name": center["block_name"]
                           }
                    refined_pincodes.append(tmp)
            if len(refined_pincodes) > 0:
                print(
                    "\n List of all available centers : \n you can enter other pincodes too to avoid those center in future\n")
                display_table(refined_pincodes)

            else:
                print(
                    "\n No available centers found at present.. you can how ever add the pincodes to exclude the centers if they become available  \n")
            excluded_pincodes = []
            pincodes = input(
                "Enter comma separated  pincodes to exclude: \n(you can enter pincodes to avoid those center in future)\n")
            for idx, pincode in enumerate(pincodes.split(",")):
                if not pincode or len(pincode) < 6:
                    print(f"Ignoring invalid pincode: {pincode}")
                    continue
                pincode = {'pincode': pincode}
                excluded_pincodes.append(pincode)
            return excluded_pincodes
        else:
            print("\n No centers available on: " + str(INP_DATE))

    else:
        print(response.status_code)
        pass


def get_districts(request_header):
    """
    This function
        1. Lists all states, prompts to select one,
        2. Lists all districts in that state, prompts to select required ones, and
        3. Returns the list of districts as list(dict)
    """
    states = requests.get(
        "https://cdn-api.co-vin.in/api/v2/admin/location/states", headers=request_header
    )

    if states.status_code == 200:
        states = states.json()["states"]

        refined_states = []
        for state in states:
            tmp = {"state": state["state_name"]}
            refined_states.append(tmp)

        display_table(refined_states)
        state = int(input("\nEnter State index: "))
        state_id = states[state - 1]["state_id"]

        districts = requests.get(
            f"https://cdn-api.co-vin.in/api/v2/admin/location/districts/{state_id}",
            headers=request_header,
        )

        if districts.status_code == 200:
            districts = districts.json()["districts"]

            refined_districts = []
            for district in districts:
                tmp = {"district": district["district_name"]}
                refined_districts.append(tmp)

            display_table(refined_districts)
            reqd_districts = input(
                "\nEnter comma separated index numbers of districts to monitor : "
            )
            districts_idx = [int(idx) - 1 for idx in reqd_districts.split(",")]
            reqd_districts = [
                {
                    "district_id": item["district_id"],
                    "district_name": item["district_name"],
                    "alert_freq": 440 + ((2 * idx) * 110),
                }
                for idx, item in enumerate(districts)
                if idx in districts_idx
            ]

            print(f"Selected districts: ")
            display_table(reqd_districts)

            return reqd_districts

        else:
            print("Unable to fetch districts")
            print(districts.status_code)
            print(districts.text)
            os.system("pause")
            sys.exit(1)

    else:
        print("Unable to fetch states")
        print(states.status_code)
        print(states.text)
        os.system("pause")
        sys.exit(1)


def fetch_beneficiaries(request_header):
    return requests.get(BENEFICIARIES_URL, headers=request_header)


def get_required_beneficiaries(request_header, beneficiaries):
    """
    This function
        1. Fetches all beneficiaries registered under the mobile number,
        2. Prompts user to select the applicable beneficiaries, and
        3. Returns the list of beneficiaries as list(dict)
    """

    refined_beneficiaries = []

    for beneficiary in beneficiaries:
        beneficiary["age"] = datetime.datetime.today().year - int(
            beneficiary["birth_year"]
        )

        if beneficiary["vaccination_status"] == "Partially Vaccinated" and len(beneficiary["dose2_date"]) == 0:
            dose2_date_calculated = vaccine_dose2_duedate(beneficiary["vaccine"], beneficiary["dose1_date"])
            beneficiary["dose2_date"] = dose2_date_calculated

        tmp = {
            "bref_id": beneficiary["beneficiary_reference_id"],
            "name": beneficiary["name"],
            "vaccine": beneficiary["vaccine"],
            "age": beneficiary["age"],
            "status": beneficiary["vaccination_status"],
            "birth_year": beneficiary["birth_year"],
            "mobile_number": beneficiary["mobile_number"],
            "photo_id_type": beneficiary["photo_id_type"],
            "photo_id_number": beneficiary["photo_id_number"],
            "dose1_date": beneficiary["dose1_date"],
            "dose2_date": beneficiary["dose2_date"],
        }

        refined_beneficiaries.append(tmp)

    display_table(refined_beneficiaries)
    print(
        """
    ################# IMPORTANT NOTES #################
    # 1. While selecting beneficiaries, make sure that selected beneficiaries are all taking the same dose: either first OR second.
    #    Please do no try to club together booking for first dose for one beneficiary and second dose for another beneficiary.
    #
    # 2. While selecting beneficiaries, also make sure that beneficiaries selected for second dose are all taking the same vaccine: COVISHIELD OR COVAXIN.
    #    Please do no try to club together booking for beneficiary taking COVISHIELD with beneficiary taking COVAXIN.
    #
    # 3. If you're selecting multiple beneficiaries, make sure all are of the same age group (45+ or 18+) as defined by the govt.
    #    Please do not try to club together booking for younger and older beneficiaries.
    ###################################################
    """
    )
    reqd_beneficiaries = input(
        "Enter comma separated index numbers of beneficiaries to book for : "
    )
    beneficiary_idx = [int(idx) - 1 for idx in reqd_beneficiaries.split(",")]
    reqd_beneficiaries = [
        {
            "bref_id": item["bref_id"],
            "name": item["name"],
            "vaccine": item["vaccine"],
            "age": item["age"],
            "status": item["status"],
            "dose1_date": item["dose1_date"],
            "dose2_date": item["dose2_date"],

        }
        for idx, item in enumerate(refined_beneficiaries)
        if idx in beneficiary_idx
    ]

    print(f"Selected beneficiaries: ")
    display_table(reqd_beneficiaries)

    # trying to check and reschedule appointments   ######

    return reqd_beneficiaries


def clear_bucket_and_send_OTP(storage_url, mobile, request_header):
    print("clearing OTP bucket: " + storage_url)
    response = requests.put(storage_url, data={})
    data = {
        "mobile": mobile,
        "secret": "U2FsdGVkX1+z/4Nr9nta+2DrVJSv7KS6VoQUSQ1ZXYDx/CJUkWxFYG6P3iM/VW+6jLQ9RDQVzp/RcZ8kbT41xw==",
    }
    print(f"Requesting OTP with mobile number {mobile}..")
    txnId = requests.post(
        url="https://cdn-api.co-vin.in/api/v2/auth/generateMobileOTP",
        json=data,
        headers=request_header,
    )

    if txnId.status_code == 200:
        txnId = txnId.json()["txnId"]
    else:
        print("Unable to Create OTP")
        print(txnId.text)
        time.sleep(5)  # Safety net against rate limit
        txnId = None
    return txnId


def check_calendar_by_district(
        request_header,
        vaccine_type,
        location_dtls,
        start_date,
        minimum_slots,
        min_age_booking,
        fee_type,
        dose_num,
        excluded_pincodes
):
    """
    This function
        1. Takes details required to check vaccination calendar
        2. Filters result by minimum number of slots available
        3. Returns False if token is invalid
        4. Returns list of vaccination centers & slots if available
    """
    try:
        print(
            "==================================================================================="
        )
        today = datetime.datetime.today()
        base_url = CALENDAR_URL_DISTRICT

        if vaccine_type:
            base_url += f"&vaccine={vaccine_type}"

        options = []
        for location in location_dtls:
            resp = requests.get(
                base_url.format(location["district_id"], start_date),
                headers=request_header,
            )

            if resp.status_code == 401:
                print("TOKEN INVALID")
                return False

            elif resp.status_code == 200:
                resp = resp.json()

                resp = filter_centers_by_age(resp, min_age_booking)
                if len(excluded_pincodes) > 1:
                    resp = filer_by_excluded_pincodes(resp, excluded_pincodes)

                if "centers" in resp:
                    print(
                        f" Total Centers available in {location['district_name']} from {start_date} as of {today.strftime('%Y-%m-%d %H:%M:%S')}: {len(resp['centers'])}"
                    )
                    options += viable_options(
                        resp, minimum_slots, min_age_booking, fee_type, dose_num
                    )

            else:
                pass

        for location in location_dtls:
            if location["district_name"] in [option["district"] for option in options]:
                for _ in range(2):
                    beep(location["alert_freq"], 150)
        return options

    except Exception as e:
        print(str(e))
        beep(WARNING_BEEP_DURATION[0], WARNING_BEEP_DURATION[1])


def generate_token_OTP(mobile, request_header, otp_validation_header):
    """
    This function generate OTP and returns a new token or None when not able to get token
    """
    storage_url = "https://kvdb.io/SK2XsE52VMgzwaZMKAK2pc/" + mobile

    txnId = clear_bucket_and_send_OTP(storage_url, mobile, request_header)

    if txnId is None:
        return txnId

    time.sleep(10)
    t_end = time.time() + 60 * 3  # try to read OTP for at most 3 minutes
    while time.time() < t_end:
        response = requests.get(storage_url)
        if response.status_code == 200:
            print("OTP SMS is:" + response.text)
            print("OTP SMS len is:" + str(len(response.text)))

            OTP = response.text
            OTP = OTP.replace("Your OTP to register/access CoWIN is ", "")
            OTP = OTP.replace(". It will be valid for 3 minutes. - CoWIN", "")
            if not OTP:
                time.sleep(5)
                continue
            break
        else:
            # Hope it won't 500 a little later, wait for 5 sec and try again
            print("error fetching OTP API:" + response.text)
            time.sleep(5)

    if not OTP:
        return None

    print("Parsed OTP:" + OTP)

    data = {"otp": sha256(str(OTP.strip()).encode("utf-8")).hexdigest(), "txnId": txnId}
    print(f"Validating OTP..")

    token = requests.post(
        url="https://cdn-api.co-vin.in/api/v2/auth/validateMobileOtp",
        json=data,
        headers=otp_validation_header,
    )
    if token.status_code == 200:
        token = token.json()["token"]
    else:
        print("Unable to Validate OTP")
        print(token.text)
        return None

    print(f"Token Generated: {token}")
    return token


def check_calendar_by_pincode(
        request_header,
        vaccine_type,
        location_dtls,
        start_date,
        minimum_slots,
        min_age_booking,
        fee_type,
        dose_num
):
    """
    This function
        1. Takes details required to check vaccination calendar
        2. Filters result by minimum number of slots available
        3. Returns False if token is invalid
        4. Returns list of vaccination centers & slots if available
    """
    try:
        print(
            "==================================================================================="
        )
        today = datetime.datetime.today()
        base_url = CALENDAR_URL_PINCODE

        if vaccine_type:
            base_url += f"&vaccine={vaccine_type}"

        options = []
        for location in location_dtls:
            resp = requests.get(
                base_url.format(location["pincode"], start_date), headers=request_header
            )

            if resp.status_code == 401:
                print("TOKEN INVALID")
                return False

            elif resp.status_code == 200:
                resp = resp.json()

                resp = filter_centers_by_age(resp, min_age_booking)

                if "centers" in resp:
                    print(
                        f"Centers available in {location['pincode']} from {start_date} as of {today.strftime('%Y-%m-%d %H:%M:%S')}: {len(resp['centers'])}"
                    )

                    options += viable_options(
                        resp, minimum_slots, min_age_booking, fee_type, dose_num
                    )

            else:
                print(f"\nno centers in response for pincode : {location['pincode']}")
                pass

        for location in location_dtls:
            if int(location["pincode"]) in [option["pincode"] for option in options]:
                for _ in range(2):
                    beep(location["alert_freq"], 150)

        return options

    except Exception as e:
        print(str(e))
        beep(WARNING_BEEP_DURATION[0], WARNING_BEEP_DURATION[1])


def generate_token_OTP_manual(mobile, request_header, otp_validation_header):
    """
    This function generate OTP and returns a new token
    """

    if not mobile:
        print("Mobile number cannot be empty")
        os.system('pause')
        sys.exit()

    valid_token = False
    while not valid_token:
        try:
            data = {"mobile": mobile,
                    "secret": "U2FsdGVkX1+z/4Nr9nta+2DrVJSv7KS6VoQUSQ1ZXYDx/CJUkWxFYG6P3iM/VW+6jLQ9RDQVzp/RcZ8kbT41xw=="
                    }
            txnId = requests.post(url=OTP_PRO_URL, json=data, headers=request_header)

            if txnId.status_code == 200:
                print(f"Successfully requested OTP for mobile number {mobile} at {datetime.datetime.today()}..")
                txnId = txnId.json()['txnId']

                OTP = input("Enter OTP (If this takes more than 2 minutes, press Enter to retry): ")
                if OTP:
                    data = {"otp": sha256(str(OTP).encode('utf-8')).hexdigest(), "txnId": txnId}
                    print(f"Validating OTP..")

                    token = requests.post(url='https://cdn-api.co-vin.in/api/v2/auth/validateMobileOtp', json=data,
                                          headers=otp_validation_header)
                    if token.status_code == 200:
                        token = token.json()['token']
                        print(f'Token Generated: {token}')
                        valid_token = True
                        return token

                    else:
                        print('Unable to Validate OTP')
                        print(f"Response: {token.text}")

                        retry = input(f"Retry with {mobile} ? (y/n Default y): ")
                        retry = retry if retry else 'y'
                        if retry == 'y':
                            pass
                        else:
                            sys.exit()

            else:
                print('Unable to Generate OTP')
                print(txnId.status_code, txnId.text)

                retry = input(f"Retry with {mobile} ? (y/n Default y): ")
                retry = retry if retry else 'y'
                if retry.lower() == 'y':
                    pass
                else:
                    sys.exit()

        except Exception as e:
            print(str(e))


def collect_user_details(request_header):
    # Get Beneficiaries
    print("Fetching registered beneficiaries.. ")
    beneficiaries = fetch_beneficiaries(request_header)
    if beneficiaries.status_code == 200:
        beneficiaries = beneficiaries.json()["beneficiaries"]
        beneficiary_dtls = get_required_beneficiaries(request_header, beneficiaries)
    else:
        print("Unable to fetch beneficiaries")
        print(beneficiaries.status_code)
        print(beneficiaries.text)
        os.system("pause")

    if len(beneficiary_dtls) == 0:
        print("There should be at least one beneficiary. Exiting.")
        os.system("pause")
        sys.exit(1)
    active_appointment = check_active_appointment(beneficiary_dtls, beneficiaries)
    if len(active_appointment) > 0:
        print("\nFollowing users have active appointments scheduled : \n")
        display_table(active_appointment)
        print(
            "\n=========================       Active appointments found      ===========================\n  "
            "=========================Reschedule appointment or remove the user ================")
        reschedule_inp = input(print(f"\nDo you want to reschedule the active appointment? \n "
                                     f"*************    enter    c    to cancel appointments     **********\n"
                                     f"*************    you can chose to reschedule only one beneficiary at a time     **********\n"
                                     f"if you select   n   beneficiary having ACTIVE APPOINTMENT will NOT be considered for booking \n"
                                     f"if you select   y   beneficiary with NO APPOINTMENT will NOT be considered for booking (y/n): default n"))
        if reschedule_inp.lower() in ["y", "n", "c"] and reschedule_inp.lower() == "y":
            if len(beneficiary_dtls) == 1:
                print("\n Rescheduling appointments for : \n")
                beneficiary_dtls = active_appointment[:]
                display_table(active_appointment)
            else:
                beneficiary_dtls = collect_reschedule_appointment_data(active_appointment)
                print("\n       Rescheduling appointments for :        \n")
                display_table(active_appointment)

        elif reschedule_inp.lower() == 'c':
            cancel_appointments(request_header, active_appointment)

        else:
            req_list = []
            seen = set()
            for active_beneficiary in list(active_appointment):
                seen.add(active_beneficiary['bref_id'])
            for filter_beneficiary in beneficiary_dtls:
                if str(filter_beneficiary['bref_id']) not in seen:
                    req_list.append(filter_beneficiary)
            if len(req_list) > 0:
                print("\n            Continuing with...          \n")
                beneficiary_dtls = req_list[:]
                display_table(beneficiary_dtls)
            else:
                print("\n   ==========   No eligible beneficiary selected for booking.. exiting script..  =======  \n")
                print(
                    "\n **********************************************************************************************\n")
                os.system("pause")
                sys.exit(1)
    else:
        reschedule_inp = None

    # Make sure all beneficiaries have the same type of vaccine
    vaccine_types = [beneficiary["vaccine"] for beneficiary in beneficiary_dtls]
    vaccines = Counter(vaccine_types)

    if len(vaccines.keys()) != 1:
        print(
            f"All beneficiaries in one attempt should have the same vaccine type. Found {len(vaccines.keys())}"
        )
        os.system("pause")
        sys.exit(1)

    vaccine_type = vaccine_types[0]
    if not vaccine_type:
        print(
            "\n================================= Vaccine Info =================================\n"
        )
        vaccine_type = get_vaccine_preference()

    print(
        "\n================================= Starting Date =================================\n"
    )

    if all([beneficiary['status'] == 'Partially Vaccinated' for beneficiary in beneficiary_dtls]):
        today = datetime.datetime.today()
        today = today.strftime("%d-%m-%Y")

        ######## enabling multiple beneficiaries to book for dose 2 if dose2 dates are in past for all ############
        for beneficiary in beneficiary_dtls:
            if (datetime.datetime.strptime(beneficiary['dose2_date'], "%d-%m-%Y") - datetime.datetime.strptime(
                    str(today),
                    "%d-%m-%Y")).days > 0:
                print("\n All beneficiaries should have due dates in past...")
                os.system("pause")
                sys.exit(1)

    # Get search start date
    start_date = input(
        "\nSearch for next seven day starting from when?"
        "\nUse 1 for today, 2 for tomorrow, or provide a date in the "
        "format dd-mm-yyyy. Default 2: "
    )
    if not start_date:
        start_date = 2
    elif start_date in ["1", "2"]:
        start_date = int(start_date)
    else:
        try:
            datetime.datetime.strptime(start_date, "%d-%m-%Y")
        except ValueError:
            start_date = 2
            print('Invalid Date! Proceeding with tomorrow.')

    print(
        "\n================================= Location Info =================================\n"
    )
    search_option = input(
        """Search by Pincode? Or by State/District? \nEnter 1 for Pincode or 2 for State/District. (Default 2) : """
    )

    if not search_option or int(search_option) not in [1, 2]:
        search_option = 2
    else:
        search_option = int(search_option)
    if search_option == 2:
        # Collect vaccination center preferance
        location_dtls = get_districts(request_header)
        # exclude pincode
        exclude_option = input(
            """Do you want to avoid centers of particular pincode? y/n (default n) : """)
        if not exclude_option or exclude_option not in ["y", "n"]:
            exclude_option = "n"
        if exclude_option.lower() == "y":
            for district in location_dtls:
                get_district_id = district["district_id"]
            for district in beneficiary_dtls:
                min_age = district["age"]
            excluded_pincodes = get_all_pincodes(request_header, get_district_id, start_date, min_age)
        else:
            excluded_pincodes = None

    else:
        # Collect vaccination center preferance
        location_dtls = get_pincodes()
        excluded_pincodes = None

    print(
        "\n================================= Additional Info =================================\n"
    )

    # Set booking condition (either one after another or all at once)
    minimum_slots = input(
        f"Filter out centers with availability less than ? default (Maximum) {len(beneficiary_dtls)} : "
    )
    if minimum_slots:
        minimum_slots = (
            int(minimum_slots)
            if int(minimum_slots) == 1
            else len(beneficiary_dtls)
        )
    else:
        minimum_slots = len(beneficiary_dtls)

    # Get refresh frequency
    refresh_freq = input(
        "How often do you want to refresh the calendar (in seconds)? Default 15. Minimum 5. : "
    )
    refresh_freq = int(refresh_freq) if refresh_freq and int(refresh_freq) >= 5 else 15

    # Get preference of Free/Paid option
    fee_type = get_fee_type_preference()
    auto_book = "yes-please"

    print("\n================================= Captcha Automation =================================\n")

    captcha_automation = input("Do you want to automate captcha autofill? (api/ai/n) Default ai: "
                               "\n choosing API will require paid API key from anti captcha or 2 captcha")
    captcha_automation = "ai" if not captcha_automation else captcha_automation
    captcha_api_choice = None
    captcha_automation_api_key = None
    if captcha_automation.lower() == "api":
        captcha_api_choice = input(
            "Select your preferred API service, 0 for https://anti-captcha.com and 1 for https://2captcha.com/ ("
            "Default 0) :")
        if captcha_api_choice not in ['0', '1']: captcha_api_choice = '0'
        # filling captcha API instead of collecting form user input #
        if captcha_api_choice == '0':
            #            captcha_automation_api_key = "anti captcha api key"
            #        else:
            #            captcha_automation_api_key = "2captcha api key"
            captcha_automation_api_key = input("Enter your Anti-Captcha or 2Captcha API key: ")
    elif captcha_automation.lower() == "n":
        captcha_api_choice = None
        captcha_automation_api_key = None

    collected_details = {
        "beneficiary_dtls": beneficiary_dtls,
        "location_dtls": location_dtls,
        "search_option": search_option,
        "minimum_slots": minimum_slots,
        "refresh_freq": refresh_freq,
        "auto_book": auto_book,
        "start_date": start_date,
        "vaccine_type": vaccine_type,
        "fee_type": fee_type,
        'captcha_automation': captcha_automation,
        'captcha_api_choice': captcha_api_choice,
        'captcha_automation_api_key': captcha_automation_api_key,
        'excluded_pincodes': excluded_pincodes,
        'reschedule_inp': reschedule_inp
    }

    return collected_details


def get_vaccine_preference():
    print(
        "It seems you're trying to find a slot for your first dose. Do you have a vaccine preference?"
    )
    preference = input(
        "Enter 0 for No Preference, 1 for COVISHIELD, 2 for COVAXIN, or 3 for SPUTNIK V. Default 0 : "
    )
    preference = int(preference) if preference and int(preference) in [0, 1, 2, 3] else 0

    if preference == 1:
        return "COVISHIELD"
    elif preference == 2:
        return "COVAXIN"
    elif preference == 3:
        return "SPUTNIK V"
    else:
        return None


def get_fee_type_preference():
    print("\nDo you have a fee type preference?")
    preference = input(
        "Enter 0 for No Preference, 1 for Free Only, or 2 for Paid Only. Default 0 : "
    )
    preference = int(preference) if preference and int(preference) in [0, 1, 2] else 0

    if preference == 1:
        return ["Free"]
    elif preference == 2:
        return ["Paid"]
    else:
        return ["Free", "Paid"]


def get_pincodes():
    locations = []
    pincodes = input("Enter comma separated index numbers of pincodes to monitor: ")
    for idx, pincode in enumerate(pincodes.split(",")):
        pincode = {"pincode": pincode, "alert_freq": 440 + ((2 * idx) * 110)}
        locations.append(pincode)
    return locations


def get_dose_num(collected_details):
    # If any person has vaccine detail populated, we imply that they'll be taking second dose
    # Note: Based on the assumption that everyone have the *EXACT SAME* vaccine status
    if any(detail['vaccine']
           for detail in collected_details["beneficiary_dtls"]):
        return 2
    return 1


def display_table(dict_list):
    """
    This function
        1. Takes a list of dictionary
        2. Add an Index column, and
        3. Displays the data in tabular format
    """
    header = ["idx"] + list(dict_list[0].keys())
    rows = [[idx + 1] + list(x.values()) for idx, x in enumerate(dict_list)]
    print(tabulate.tabulate(rows, header, tablefmt="grid"))


def display_info_dict(details):
    for key, value in details.items():
        if isinstance(value, list):
            if all(isinstance(item, dict) for item in value):
                print(f"\t{key}:")
                display_table(value)
            else:
                print(f"\t{key}\t: {value}")
        else:
            print(f"\t{key}\t: {value}")


def filter_centers_by_age(resp, min_age_booking):
    if min_age_booking >= 45:
        center_age_filter = 45
    else:
        center_age_filter = 18

    if "centers" in resp:
        for center in list(resp["centers"]):
            for session in list(center["sessions"]):
                if session['min_age_limit'] != center_age_filter:
                    center["sessions"].remove(session)
                    if len(center["sessions"]) == 0:
                        resp["centers"].remove(center)

    return resp


def get_min_age(beneficiary_dtls):
    """
    This function returns a min age argument, based on age of all beneficiaries
    :param beneficiary_dtls:
    :return: min_age:int
    """
    age_list = [item["age"] for item in beneficiary_dtls]
    min_age = min(age_list)
    return min_age


def generate_captcha(request_header, captcha_automation, api_key, captcha_api_choice):
    print(
        "================================= GETTING CAPTCHA =================================================="
    )
    resp = requests.post(CAPTCHA_URL, headers=request_header)
    print(f'Captcha Response Code: {resp.status_code}')

    if resp.status_code == 200 and captcha_automation == "n":
        return captcha_builder_manual(resp.json())
    elif resp.status_code == 200 and captcha_automation == "api":
        return captcha_builder_api(resp.json(), api_key, captcha_api_choice)
    elif resp.status_code == 200 and captcha_automation == "ai":
        return captcha_builder_auto(resp.json())


def filer_by_excluded_pincodes(resp, excluded_pincodes):
    if "centers" in resp:
        available_center = resp['centers']
        pin_excluded_centers = []

        seen = set()
        for pincodes in list(excluded_pincodes):
            if pincodes['pincode'] not in seen:
                seen.add(pincodes['pincode'])
        for center in available_center:
            if str(center['pincode']) not in seen:
                pin_excluded_centers.append(center)
        resp['centers'] = pin_excluded_centers
    return resp


def vaccine_dose2_duedate(vaccine_type, dose1_date):
    """
    This function
        1.Checks the vaccine type
        2.Returns the appropriate due date for the vaccine type
    """
    if vaccine_type == "COVISHIELD":
        dose1 = datetime.datetime.strptime(dose1_date, "%d-%m-%Y")
        covishield_due_date = dose1 + datetime.timedelta(84)
        return covishield_due_date.strftime("%d-%m-%Y")
    elif vaccine_type == "COVAXIN":
        dose1 = datetime.datetime.strptime(dose1_date, "%d-%m-%Y")
        covaxin_due_date = dose1 + datetime.timedelta(28)
        return covaxin_due_date.strftime("%d-%m-%Y")
    elif vaccine_type == "SPUTNIK V":
        dose1 = datetime.datetime.strptime(dose1_date, "%d-%m-%Y")
        sputnikV_due_date = dose1 + datetime.timedelta(21)
        return sputnikV_due_date.strftime("%d-%m-%Y")


def get_saved_user_info(filename):
    with open(filename, "r") as f:
        data = json.load(f)

    return data


def viable_options(resp, minimum_slots, min_age_booking, fee_type, dose_num):
    options = []
    if len(resp["centers"]) >= 0:
        for center in resp["centers"]:
            for session in center["sessions"]:
                available_capacity = min(session[f'available_capacity_dose{dose_num}'], session['available_capacity'])
                if (
                        (available_capacity >= minimum_slots)
                        and (session["min_age_limit"] <= min_age_booking)
                        and (center["fee_type"] in fee_type)
                ):
                    out = {
                        "name": center["name"],
                        "district": center["district_name"],
                        "pincode": center["pincode"],
                        "center_id": center["center_id"],
                        "vaccine": session["vaccine"],
                        "fee_type": center["fee_type"],
                        "fee": session.get("fee", "0"),
                        "available": available_capacity,
                        "date": session["date"],
                        "slots": session["slots"],
                        "session_id": session["session_id"],
                    }
                    options.append(out)

                else:
                    pass
    else:
        pass
    if len(options) > 0:
        print("\n **************   Centers with available slots found   ****************\n")
        display_table(options)
    return options


def save_user_info(filename, details):
    if not details['excluded_pincodes']:
        details['excluded_pincodes'] = None
    print(
        "\n================================= Save Info =================================\n"
    )
    save_info = input(
        "Would you like to save this as a JSON file for easy use next time?: (y/n Default y): "
    )
    save_info = save_info if save_info else "y"
    if save_info.lower() == "y":
        with open(filename, "w") as f:
            # JSON pretty save to file
            json.dump(details, f, sort_keys=True, indent=4)
        print(f"Info saved to {filename} in {os.getcwd()}")
    else:
        print("User Details has not been saved")


def confirm_and_proceed(collected_details):
    print(
        "\n================================= Confirm Info =================================\n"
    )
    display_info_dict(collected_details)

    confirm = input("\nProceed with above info (y/n Default y) : ")
    confirm = confirm if confirm else "y"
    if confirm.lower() != "y":
        print("Details not confirmed. Exiting process.")
        os.system("pause")
        sys.exit()


def collect_reschedule_appointment_data(active_appointment_detailed):
    reschedule_data = []
    while len(reschedule_data) == 0:
        reschedule_input = int(
            input(print(f"select the user you want to reschedule the appointment \n CHOOSE ONLY ONE USER\n")))
        if reschedule_input:
            reschedule_idx = [int(idx) - 1 for idx in active_appointment_detailed.split(",")]
            data = [
                {
                    "bref_id": item["bref_id"],
                    "name": item["name"],
                    "appointment_id": item["appointments"],
                    "slot": item["slot"],

                }
                for idx, item in enumerate(list(active_appointment_detailed))
                if idx in reschedule_idx
            ]
            reschedule_data.append({**data})
            return reschedule_data
        else:
            print("wrong input.. exiting....")
            os.system('pause')
            sys.exit()


def check_active_appointment(reqired_beneficiaries, beneficiaries):
    active_appointments_list = []
    beneficiary_ref_ids = [beneficiary["bref_id"]
                           for beneficiary in reqired_beneficiaries]
    beneficiary_dtls = [beneficiary
                        for beneficiary in beneficiaries
                        if beneficiary['beneficiary_reference_id'] in beneficiary_ref_ids]

    for beneficiary in beneficiary_dtls:
        expected_appointments = (1 if beneficiary['vaccination_status'] == "Partially Vaccinated" else 0)
        if len(beneficiary["appointments"]) > expected_appointments:
            beneficiary["age"] = datetime.datetime.today().year - int(
                beneficiary["birth_year"])
            data = beneficiary['appointments'][expected_appointments]
            beneficiary_data = {'center_name': data['name'],
                                'state_name': data['state_name'],
                                'dose': data['dose'],
                                'date': data['date'],
                                'slot': data['slot'],
                                'appointment_id': data['appointment_id'],
                                'session_id': data['session_id']
                                }
            active_appointments_list.append(
                {"bref_id": beneficiary["beneficiary_reference_id"],
                 "beneficiary": beneficiary['name'], 'age': beneficiary["age"], **beneficiary_data,
                 'status': beneficiary['vaccination_status'],
                 'vaccine': beneficiary['vaccine'],
                 'birth_year': beneficiary['birth_year'],
                 "mobile_number": beneficiary["mobile_number"],

                 }
            )
        return active_appointments_list


def reschedule_appointment(request_header, details, mobile, generate_captcha_pref, api_key=None,
                           captcha_api_choice=None):
    try:
        valid_captcha = True
        while valid_captcha:
            captcha = generate_captcha(request_header, generate_captcha_pref, api_key, captcha_api_choice)
            details["captcha"] = captcha

            print(
                "================================= ATTEMPTING BOOKING =================================================="
            )

            resp = requests.post(RESCHEDULE_URL, headers=request_header, json=details)
            print(f"Booking Response Code: {resp.status_code}")
            print(f"Booking Response : {resp.text}")

            if resp.status_code == 401:
                print("TOKEN INVALID")
                return False

            elif resp.status_code == 200:
                beep(WARNING_BEEP_DURATION[0], WARNING_BEEP_DURATION[1])
                print(
                    "##############    RESCHEDULED!  ############################    RESCHEDULED!  ##############"
                )
                print(
                    "                        YOUR APPOINTMENT HAS BEEN RESCHEDULED                       "
                )
                re_appointment_id = resp.text
                re_appointment_id = (re_appointment_id[32:68])
                response = requests.get(
                    "https://cdn-api.co-vin.in/api/v2/appointment/appointmentslip/download?appointment_id={}".format(
                        re_appointment_id), headers=request_header)
                if response.status_code == 200:
                    filename = "appointment_slip" + re_appointment_id
                    with open(filename, 'wb') as f:
                        f.write(response.content)
                else:
                    print("unable to download appointment slip")
                    print(f"Response: {resp.status_code} : {resp.text}")

                print("\nPress any key twice to exit program.")
                #                return True
                os.system("pause")
                os.system("pause")
                sys.exit()

            elif resp.status_code == 409:
                print(f"Response: {resp.status_code} : {resp.text}")
                try:
                    data = resp.json()
                    # Response: 409 : {"errorCode":"APPOIN0040","error":"This vaccination center is completely booked for the selected date. Please try another date or vaccination center."}
                    if data.get("errorCode", '') == 'APPOIN0040':
                        time.sleep(2)
                        return 1
                except Exception as e:
                    print(str(e))
                return 2
            elif resp.status_code == 400:
                print(f"Response: {resp.status_code} : {resp.text}")
                # {"errorCode":"APPOIN0011","error":"You have selected the same vaccination center and date as that of your current appointment. Please select a different vaccination center or the date for rescheduling."}
                pass
            elif resp.status_code >= 500:
                print(f"Response: {resp.status_code} : {resp.text}")
                # Server error at the time of high booking
                # Response: 500 : {"message":"Throughput exceeds the current capacity of your table or index.....","code":"ThrottlingException","statusCode":400,"retryable":true}
                pass
            else:
                print(f"Response: {resp.status_code} : {resp.text}")
                return True

    except Exception as e:
        print(str(e))
        beep(WARNING_BEEP_DURATION[0], WARNING_BEEP_DURATION[1])


def delete_unwanted_display_value(active_appointment):
    for beneficiary in active_appointment:
        del beneficiary['status']
        del beneficiary['birth_year']
        del beneficiary['mobile_number']
        del beneficiary['appointment_id']
        del beneficiary['session_id']
    return active_appointment


def cancel_appointments(request_header, active_appointments):
    appointment_to_cancel = []

    for beneficiary in list(active_appointments):
        tmp = {
            'appointment_id': beneficiary["appointment_id"],
            'beneficiariesToCancel': beneficiary["bref_id"],
            'name': beneficiary["beneficiary"],
        }
        appointment_to_cancel.append(tmp)

    for value_present in appointment_to_cancel:
        data = {
            'appointment_id': value_present['appointment_id'],
            'beneficiariesToCancel': [value_present['beneficiariesToCancel']]
        }
        response = requests.post(CANCEL_URL, headers=request_header, json=data)
        if response.status_code == 204:
            print(f"appointment of " + str(value_present['name']) + " has been cancelled")
        else:
            print("\n UNABLE TO CANCEL THE APPOINTMENT   \n")
            print(f"Response: {response.status_code} : {response.text}")
            os.system('pause')
            sys.exit()
    print("====================   Appointments have been cancelled successfully    ===============")
    os.system('pause')
    sys.exit()
