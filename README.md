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


#### For the correct work of the application you should configure RPC :26657 and REST :1317 endpoints

##### ex: http://8.8.8.8:26657, http://8.8.8.8:1317


<details>
  <summary>Installing:</summary>
  
  #### Technically, the installation itself is cloning the repo, setting dependencies, and providing 6 variables

```sh
$ cd && git clone https://github.com/Northa/cosmosvanity.git && cd cosmosvanity
$ sudo apt install python3-pip
$ pip3 install pipenv
$ pipenv sync

```
  Next open config.py in editor and replace required variables with your values.
  
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

