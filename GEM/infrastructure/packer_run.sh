echo "Running packer"

echo "Fetching packer"
wget https://releases.hashicorp.com/packer/1.7.2/packer_1.7.2_linux_amd64.zip
unzip packer_1.7.2_linux_amd64.zip
chmod a+x packer
mv packer /usr/local/bin
export PATH=/usr/local/bin:$PATH

echo "Validating packer json"
packer validate packer.json

echo "Creating AMI"
packer build packer.json
