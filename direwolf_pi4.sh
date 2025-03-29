echo "Starting direwolf_pi4 script..."
smbclient -U cpusu%tiger123 //192.168.86.74/terminal -c "ls" -D "Checking share access"
# Retry loop for smbclient fetch
for i in {1..3}
do
    echo "Attempt \ to fetch temp/fake_direwolf.py..."
    sshpass -p "tiger1" smbclient -U cpusu%tiger123 //192.168.86.74/terminal -c "get temp/fake_direwolf.py /tmp/fake_direwolf.py" -D "Fetched fake_direwolf.py" && break
    echo "Fetch attempt \ failed, retrying..."
    sleep 5
done
ls -l /tmp/fake_direwolf.py
sudo mv /tmp/fake_direwolf.py /home/aprs/terminal/fake_direwolf.py
sudo chmod 775 /home/aprs/terminal/fake_direwolf.py
sudo chgrp users /home/aprs/terminal/fake_direwolf.py
ls -ld /home/aprs/terminal/
pkill -f "python3 /home/aprs/terminal/fake_direwolf.py"
python3 /home/aprs/terminal/fake_direwolf.py
bash
