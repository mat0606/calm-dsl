
sudo yum install -y https://dl.fedoraproject.org/pub/epel/epel-release-latest-8.noarch.rpm
sudo yum-config-manager --add-repo=http://mirror.centos.org/centos-7/7.9.2009/extras/x86_64
sudo yum -y update
sudo yum -y install realmd libnss-sss libpam-sss sssd sssd-tools adcli samba-common samba-common-bin samba-common-tools oddjob oddjob-mkhomedir packagekit 