
Requirements for the Script: gminer_negative_price.py

To run the provided script on a Linux system, you need the following requirements:

1. Python 3 and pip
Ensure you have Python 3 installed, which typically comes pre-installed on most modern Linux distributions.

Install pip:

sudo apt-get update
sudo apt-get install python3-pip

2. Required Python Modules
Install the required Python modules:

pip install requests

3. Tkinter
Tkinter is required for the GUI. Install it using:

sudo apt-get install python3-tk

4. A Compatible Miner Software

You must have a mining program that supports command-line arguments as used in the script. Ensure it is installed and executable on your system. For example:

https://github.com/develsoftware/gminerrelease/releases
https://github.com/develsoftware/GMinerRelease/releases/download/3.44/gminer_3_44_linux64.tar.xz

chmod +x ./miner

Programmet laddar ner elpriserna och så kan du ställe in vilket pris det måste vara under för miningen
med gminer ska starta , sen när priset går över slutar den mina, man kan ställa in elområde SE1,SE2,SE3 och SE4
