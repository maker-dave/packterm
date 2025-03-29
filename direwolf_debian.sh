echo "Starting direwolf_debian script..."
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
sudo mv /tmp/fake_direwolf.py /opt/terminal_client/fake_direwolf.py
sudo chmod 775 /opt/terminal_client/fake_direwolf.py
sudo chgrp users /opt/terminal_client/fake_direwolf.py
ls -ld /opt/terminal_client/
pkill -f "python3 /opt/terminal_client/fake_direwolf.py"
python3 /opt/terminal_client/fake_direwolf.py
bash
