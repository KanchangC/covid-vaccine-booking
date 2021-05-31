# COVID-19 Vaccination Slot Booking Script
## Update:
### **We are getting all kinds of attention now - which I do not want to handle. So there won't be any additional commits to this project. It has been put on indefinite hold.**



### Important: 
- This is a proof of concept project. I do NOT endorse or condone, in any shape or form, automating any monitoring/booking tasks. **Use at your own risk.**
- This CANNOT book slots automatically. It doesn't skip any of the steps that a normal user would have to take on the official portal. You will still have to enter the OTP and Captcha.
- Do NOT use unless all the beneficiaries selected are supposed to get the same vaccine and dose. 
- There is no option to register new mobile or add beneficiaries. This can be used only after beneficiary has been added through the official app/site.
- This goes without saying but, once you get your shot, please do help out any underprivileged people around you who may not have a laptop or the know-how. For instance any sort of domestic help, or the staff in your local grocery store, or literally the thousands of people who don't have the knowledge  or luxury we do.
- API Details (read the first paragraph at least): https://apisetu.gov.in/public/marketplace/api/cowin/cowin-public-v2
- BMC Link: https://www.buymeacoffee.com/pallupz
    - All donations, as they materialize, will be split equally between COVID Kerala CMDRF and a centre for cerebral palsied children with multiple handicaps.
- Discord ID for DMs: pallupz#5726
- And finally, I know code quality isn't great. Suggestions are welcome.

### What this script do

1. Check availabilty of centers and slots at prefered location --> search by district or pincodes)
2. Fliter out unwanted centeres based on pincodes of a particular district 
3. Option to automate the booking
4. Book for all selected beneficiaries at once
5. Book for a multiple beneficiary one after another 
--> provides an edge when trying to book in off hours when getting more than 1 slot is difficult but you don't want to sit and wait to schedule the scipt for other beneficiary after getting one appointment
5. Reschedule active appointment 
6. Cancel active appointment 
7. Download appointment slip


### Usage:

EXE file that was being built via ```pyinstaller``` on GitHub Actions does not work anymore but the **Python 3.7** code still does. If you don't already have Python and do not know how to set it up, instructions are at the bottom. It's not complicated at all and takes literally 5 minutes. Please do that and come back here.

Download this code as zip, and extract it to some folder like ```C:\temp\covid-vaccine-booking```. Going by this structure, the py files should be in ```C:\temp\covid-vaccine-booking\src```. 

Open command prompt and run ```cd C:\temp\covid-vaccine-booking```

Install all the dependencies with the below. This is a one-time activity (for anyone not familiar with Python)
```
pip install -r requirements.txt
```

If you're on Linux or MacOS, install the SoX ([Sound eXchange](http://sox.sourceforge.net/ "Sound eXchange")) before running the Python script. To install, run:

Ubuntu:
```
sudo apt install sox
```
MacOS:
```
brew install sox
```

Finally, run the script file as shown below:
```
python3 src\covid-vaccine-slot-booking.py
```

### Python 3.7.3 Installation in Windows
- Check if Python is already installed by opening command prompt and running ```python --version```.
- If the above command returns ```Python <some-version-number>``` you're probably good - provided version number is above 3.6
- If Python's not installed, command would say something like: ```'python' is not recognized as an internal or external command, operable program or batch file.```
- If so, download the installer from: https://www.python.org/ftp/python/3.7.3/python-3.7.3-amd64.exe
- Run that. In the first screen of installer, there will be an option at the bottom to "Add Python 3.7 to Path". Make sure to select it.
- Open command prompt and run ```python --version```. If everything went well it should say ```Python 3.7.3```
- You're all set! 

### How it works via IFTTT app on Android to feed OTP to the script
https://ifttt.com/ is used to create a SMS trigger. The trigger happens when the OTP SMS is received
The trigger sends the text of the SMS to a REST service, I have used a free service which needs 0 setup for a shared storage

Setup Guide for Android
Option 1: IFTTT
Create an account in ifttt.com (A premium paid account is recommended for a quicker response)
Create a new applet
If this..... click on Android SMS trigger
Select "New SMS received matches search" and use CoWIN as the search key
Then... Choose a service named Webhooks and then select make a web request
Paste the url: https://kvdb.io/SK2XsE52VMgzwaZMKAK2pc/XXXXXXXXXX replace XXXXXXXXXX with your phone number
Method is PUT
Content Type PlainText
Body: Add ingredient and select Text
On your android phone, install ifttt app
Login
Ensure that the battery saver mode, and all other optimizations are removed. Allow the app to read SMS. The appshould always run (This is the key for quick response).
Note: 
1. ifttt configured will ONLY read OTP received from cowin. 
2. Use IFTTT at your own risk and go through the privacy and data collection/share policy of IFTTT.
