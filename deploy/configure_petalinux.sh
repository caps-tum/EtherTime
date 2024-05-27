i=4
mac_addr="enx3c18a0d5a406"

sudo chown root:root /
sudo chmod 755 /
stat /

echo """
auto end0
iface end0 inet static
    address 10.0.0.8${i}
    netmask 255.255.255.0
""" > /etc/network/interfaces.d/internal-adapter

echo """
auto ${mac_addr}
  iface ${mac_addr} inet dhcp
  pre-up sleep 15
""" > /etc/network/interfaces.d/usb-adapter

echo "petalinux0${i}" > /etc/hostname

adduser rpi
usermod -a -G sudo,root rpi

mkdir /home/rpi/.ssh
chown rpi:rpi /home/rpi/.ssh
chmod 700 /home/rpi/.ssh
echo """
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQC/i9qjLCRzLkanWmwGDbtFBd4c0uSVt4o6tA18KdmFZhpfRmL/1EzvSF4IBc+me/aP2ySxvnn3AXAxW9lblhRClSPuhV2UtmRjRQNmjepmOGdOlrsvotJH2nOoIjb1RVPFmYoY8uThI4OnUeCAyOred8VVac9amwFX/+ToWvsiR/WSQUWKqpPJTaRnQ054YDy4ONtkp0VaN6c8IheE3uKeG7jfYT3apPXHcN2ykKigBo6hzHAzksHd/cWTHwAqO5RfcLnLqfPuFzinn4cb7FsBB9AyRDgEodQUc0pHItBtlCPeAr0ld9ACJgjygUJ1m857RbLYQJkcvDrWNksm1LVXvKMQBOLwRxRblyTh/HcDY378rUtQJrTEpOv1EYxa2s9tL4zGk1Ty2TjGfe7YbzbVenCDkfwf4E0R6FSon8m5DQFNw+jr1HJlVTZgP1XwYd+UZjqsnLbkPtp3vEP2QZIZync28Jxf5IWkk6W7CLItsQEPaUz8xnZoLX9qmcw/5Xs= rpi@cerf
ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAABBBDf+fowl76P6HzxBXJTDwDZKeyXFfIcXKH68i/9d3x5SRzDMk2ChLHILGaVtRv7ARd044qnjslpU7lj4AmYsiUI= laptop_key
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAICHEEoX4Y0TsuLifd/iabqCZxt6QUVEVBiSgloGyV4s6 second_admin_key
""" > /home/rpi/.ssh/authorized_keys
chown rpi:rpi /home/rpi/.ssh/authorized_keys
chmod 600 /home/rpi/.ssh/authorized_keys
stat /home/rpi/.ssh/authorized_keys

echo """
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQC/i9qjLCRzLkanWmwGDbtFBd4c0uSVt4o6tA18KdmFZhpfRmL/1EzvSF4IBc+me/aP2ySxvnn3AXAxW9lblhRClSPuhV2UtmRjRQNmjepmOGdOlrsvotJH2nOoIjb1RVPFmYoY8uThI4OnUeCAyOred8VVac9amwFX/+ToWvsiR/WSQUWKqpPJTaRnQ054YDy4ONtkp0VaN6c8IheE3uKeG7jfYT3apPXHcN2ykKigBo6hzHAzksHd/cWTHwAqO5RfcLnLqfPuFzinn4cb7FsBB9AyRDgEodQUc0pHItBtlCPeAr0ld9ACJgjygUJ1m857RbLYQJkcvDrWNksm1LVXvKMQBOLwRxRblyTh/HcDY378rUtQJrTEpOv1EYxa2s9tL4zGk1Ty2TjGfe7YbzbVenCDkfwf4E0R6FSon8m5DQFNw+jr1HJlVTZgP1XwYd+UZjqsnLbkPtp3vEP2QZIZync28Jxf5IWkk6W7CLItsQEPaUz8xnZoLX9qmcw/5Xs= rpi@cerf
ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAABBBDf+fowl76P6HzxBXJTDwDZKeyXFfIcXKH68i/9d3x5SRzDMk2ChLHILGaVtRv7ARd044qnjslpU7lj4AmYsiUI= laptop_key
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAICHEEoX4Y0TsuLifd/iabqCZxt6QUVEVBiSgloGyV4s6 second_admin_key
""" > /root/.ssh/authorized_keys
