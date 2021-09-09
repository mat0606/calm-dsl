sudo yum install -y firewalld
sudo systemctl enable firewalld
sudo systemctl start firewalld
sudo systemctl status firewalld
sudo firewall-cmd --permanent --zone=public --add-service=http 
sudo firewall-cmd --permanent --zone=public --add-service=https
sudo firewall-cmd --zone=public --add-port=@@{nginx_port}@@/tcp --permanent
sudo firewall-cmd --reload