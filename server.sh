echo "Starting server script..."
smbclient -U cpusu%tiger123 //192.168.86.74/terminal -c "ls" -D "Checking share access"
# Retry loop for smbclient fetch
for i in {1..3}
do
    echo "Attempt \ to fetch temp/server.py..."
    sshpass -p "tiger1" smbclient -U cpusu%tiger123 //192.168.86.74/terminal -c "get temp/server.py /tmp/server.py" -D "Fetched server.py" && break
    echo "Fetch attempt \ failed, retrying..."
    sleep 5
done
ls -l /tmp/server.py
sudo mv /tmp/server.py /home/aprs/terminal/server.py
sudo chmod 775 /home/aprs/terminal/server.py
sudo chgrp users /home/aprs/terminal/server.py
ls -ld /home/aprs/terminal/
pkill -f "python3 /home/aprs/terminal/server.py"
python3 /home/aprs/terminal/server.py
bash
