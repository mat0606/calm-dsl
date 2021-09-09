echo "Discovering the domain"
sudo realm discover @@{domain_name}@@

echo "Joining the domain"

password=@@{Domain Administrator.secret}@@
export password
#sudo echo $password | sudo /usr/sbin/realm join @@{DOMAIN_NAME}@@  -U Administrator --os-name="`uname -o`" --os-version="`uname -rsv`" --verbose 
sudo echo $password | sudo realm join -U @@{Domain Administrator.username}@@ @@{domain_name}@@ --verbose 

echo "List the domain after joining"

sudo /usr/sbin/realm list

echo "Permitting all users"
sudo realm permit --all
