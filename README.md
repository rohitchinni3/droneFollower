# droneFollower
instructions for running the drone follower
- install ssh command in your desktop and using using ssh command 
type ssh pi@192.168.20.69
password- 1234
-connect the obu and then using terminal after connecting obu to raspi ethnernet cable

-------for receiver-------

type ssh -oHostKeyAlgorithms=ssh-rsa guest@192.168.1.13
password:
now open usecases folder
type cd usecases
type cd cv2x
then type py_rx.py

------for transmitter----
type ssh -oHostKeyAlgorithms=ssh-rsa guest1@192.168.1.11
password:
now open usecases folder
type cd usecases
type cd cv2x
then type py_app_tx.py

------for raspi------
open another terminal and type 
source env/bin/activate

