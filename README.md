# COVID-19 Geographic Distribution Worldwide
Data comes from the European Centre for Disease Prevention and Control:  
https://www.ecdc.europa.eu/en/publications-data/download-todays-data-geographic-distribution-covid-19-cases-worldwide

# Demo
http://zeroday.biz/covid19/

# Install
```shell
# Install
git clone https://github.com/quarantin/covid19
cd covid19
virtualenv -p python3 env
. env/bin/activate
pip install -r requirements.txt

# Generate HTML pages
./covid19.py

# Setupp Cronjob
sudo ln -s $(pwd)/cron.sh /etc/cron.hourly/covid19
```
