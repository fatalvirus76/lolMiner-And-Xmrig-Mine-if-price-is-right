lolMiner_negative_price.py & xmrig_negative_price.py needs the following packages

Python Packages:
requests - For making API requests to fetch electricity prices.
subprocess - For starting and stopping the XMRig miner process.
time - For implementing polling intervals.
datetime - For working with time zones and timestamps.
tkinter - For the GUI interface.
threading - For running the polling function in the background.

System Requirements:
Python 3.x (Recommended: Python 3.8 or later)
XMRig installed on your system.
Installing Python Dependencies:

You can install the required Python package (requests) using:

pip install requests

Programmet hämtar aktuella timpriset och kollar det regelbundet, om priset är mindre än det
du ställt in i programmet så böejar lolMiner och Xmrig att mina, går priset över stannar
dom automatisk och börjar igen när priset är rätt
