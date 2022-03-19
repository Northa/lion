# Monitoring tool for UMEE network

## Simple, lightweight cUI blockexplorer.


#### Features:
* real time update
* signed, missed, propossed blocks
* info about validator
* node info
* node health
* telegram notifications
* hardware usage
* peggo events



#### Alerts:
  
  * Ethereum balance < 0.1 ETH  
  ![Alt text](https://github.com/Northa/lion/blob/main/screen/eth_balance.png?raw=true "ETH bal")
  * If our event_nonce behind more than 3  
  ![Alt text](https://github.com/Northa/lion/blob/main/screen/event_nonce.png?raw=true "Event nonce")
  * ETH rpc monitor. If local rpc behind infura more than 5 blocks  
  ![Alt text](https://github.com/Northa/lion/blob/main/screen/eth_rpc.png?raw=true "rpc")
  * Disk space monitor. If available disk < 10gb  
  ![Alt text](https://github.com/Northa/lion/blob/main/screen/available_disk.png?raw=true "disk")
  * Jailed status changed  
  ![Alt text](https://github.com/Northa/lion/blob/main/screen/jailed.png?raw=true "jailed")
  * Validator missing blocks  
  ![Alt text](https://github.com/Northa/lion/blob/main/screen/missed.jpg?raw=true "blocks")
  * Bond status changed  
  ![Alt text](https://github.com/Northa/lion/blob/main/screen/bond_status.png?raw=true "bond")


<details>
  <summary>Requirements:</summary>
  
  *  Ubuntu 20.04 
  *  python3.8 
  *  pip3 
  *  pipenv
  *  For the correct work of the application you should configure RPC :26657 and REST :1317 endpoints. For example:  
  http://8.8.8.8:26657 and http://8.8.8.8:1317
  
  
</details>


<details>
  <summary>Installing:</summary>
  
  #### Technically, the installation itself is cloning the repo, setting dependencies, and providing 6 variables

```sh
$ cd && git clone https://github.com/Northa/lion.git && cd lion
$ sudo apt install python3-pip
$ pip3 install pipenv
$ pipenv sync

```
  Next open ```config.py``` in editor and replace required variables with your values.
  
  Once configured you can run the app by following:
  
  ```$ pipenv run python lion.py ```
</details>

_In order to monitor hardware you have to configure node-exporter._
 _Node exporter installation described below_

<details>
  <summary>Node exporter installation:</summary>
  
```sh
 
cd && wget https://github.com/prometheus/node_exporter/releases/download/v1.3.0/node_exporter-1.3.0.linux-amd64.tar.gz && \
tar xvf node_exporter-1.3.0.linux-amd64.tar.gz && \
rm node_exporter-1.3.0.linux-amd64.tar.gz && \
sudo mv node_exporter-1.3.0.linux-amd64 node_exporter && \
chmod +x $HOME/node_exporter/node_exporter && \
sudo mv $HOME/node_exporter/node_exporter /usr/bin && \
rm -Rvf $HOME/node_exporter/

sudo tee /etc/systemd/system/exporterd.service > /dev/null <<EOF
[Unit]
Description=node_exporter
After=network-online.target
[Service]
User=$USER
ExecStart=/usr/bin/node_exporter
Restart=always
RestartSec=3
LimitNOFILE=65535
[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload && \
sudo systemctl enable exporterd && \
sudo systemctl restart exporterd
```
  
  Node exporter by default working on port :9100
  
After installation node_exporter metrics should be available
by folowing address: http://your_ip:9100

[Node_exporter guide](https://prometheus.io/docs/guides/node-exporter/)
</details>

![Alt text](https://raw.githubusercontent.com/Northa/lion/main/screen/scr1.png?raw=true "Title")

