import requests
import time
from stem import Signal
from stem.control import Controller


# india has only 3 exit nodes, so it normally gives same IP. exit node is set in /usr/local/etc/tor/torrc file in OS


def get_current_ip():
    session = requests.session()

    # TO Request URL with SOCKS over TOR
    session.proxies = {'http': 'socks5h://localhost:9050', 'https': 'socks5h://localhost:9050'}

    try:
        r = session.get('http://httpbin.org/ip')
    except Exception as e:
        print(e)
    else:
        return r.text


def renew_tor_ip():
    with Controller.from_port(port=9051) as controller:
        controller.authenticate(password="plmoknijb")
        controller.signal(Signal.NEWNYM)


for i in range(5):
    i = get_current_ip()
    print(i)
    renew_tor_ip()
    time.sleep(5)
