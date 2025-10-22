cd /mydata
curl -L -o dropbox_data.zip "https://www.dropbox.com/scl/fo/i9qth8o59f7g0q9brwqut/AOP2csAiRg98I93fuJx4n3c?rlkey=bo2i10d7917zm01tjjw82jeda&e=1&dl=1"
# 解压
apt-get update && apt-get install -y unzip  
unzip -q dropbox_data.zip -d .
rm dropbox_data.zip

mkdir /mydata/skip_data

tar -xzf unif_ycsb.tar.gz -C /mydata/skip_data
rm unif_ycsb.tar.gz


tar -xzf zipf_ycsb.tar.gz -C /mydata/skip_data
rm zipf_ycsb.tar.gz

