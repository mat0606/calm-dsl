NODE_HOST=@@{name}@@.@@{domain_name}@@
export NODE_HOST
echo $NODE_HOST

sudo hostnamectl set-hostname --static $NODE_HOST

echo "@@{address}@@ @@{name}@@.@@{domain_name}@@ @@{name}@@" | sudo tee -a /etc/hosts
echo "@@{Domain_Server_IP}@@ @@{Domain_Server}@@.@@{domain_name}@@ @@{Domain_Server}@@" | sudo tee -a /etc/hosts

echo "search dstantnx.local" | sudo tee /etc/resolv.conf
echo "nameserver @@{Domain_Server_IP}@@" | sudo tee -a /etc/resolv.conf

#sudo systemctl disable systemd-resolved
#sudo systemctl stop systemd-resolved

