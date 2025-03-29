echo "Starting client script..."
smbclient -U cpusu%tiger123 //192.168.86.74/terminal -c "ls" -D "Checking share access"
# Retry loop for smbclient fetch
for i in {1..3}
do
    echo "Attempt \ to fetch temp/terminal_client.py..."
    sshpass -p "tiger1" smbclient -U cpusu%tiger123 //192.168.86.74/terminal -c "get temp/terminal_client.py /tmp/terminal_client.py" -D "Fetched terminal_client.py" && break
    echo "Fetch attempt \ failed, retrying..."
    sleep 5
done
ls -l /tmp/terminal_client.py
echo tiger1 | sudo -S mv /tmp/terminal_client.py /opt/terminal_client/terminal_client.py
sudo chmod 775 /opt/terminal_client/terminal_client.py
sudo chgrp users /opt/terminal_client/terminal_client.py
ls -ld /opt/terminal_client/
pkill -f "python3 /opt/terminal_client/terminal_client.py"
python3 /opt/terminal_client/terminal_client.py
bash
