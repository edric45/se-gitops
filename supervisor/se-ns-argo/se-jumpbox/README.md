# se-jumpbox

An Ubuntu 24.04 desktop VM in `se-ns-argo`, reachable from a browser through an
Avi VIP. For debugging the lab: it sits in the same VPC as the cluster nodes.

| | |
|---|---|
| Desktop in the browser | `https://<VIP>/` — KasmVNC, XFCE, Chrome, VS Code, terminal |
| VS Code in the browser | `https://<VIP>:8443/` — code-server |
| SSH | `ssh jumpbox@<VIP>` — key only |
| Size | `best-effort-xlarge` (4 vCPU / 32Gi) |
| Disks | 10Gi root (OS, apps) + 100Gi data PVC at `/data` (Docker, `~/work`) |

Tools: `kubectl` + `kubectl-vsphere` (from the Supervisor), `vcf` CLI v9.0.2,
`argocd` (from our ArgoCD server), `k9s`, `helm`, `kubectx`/`kubens`, `stern`,
`yq`, `velero`, `mc`, `istioctl`, `govc`, Docker, git, and the usual network
tools (`tcpdump`, `nmap`, `mtr`, `dig`, `iperf3`, `nc`, `socat`, ...).

## Why the root disk is only 10Gi

VM Service deploys the image's 10Gi disk as a **linked clone**, and vSphere
cannot grow a disk with a parent:

    Invalid operation for device '0'. Disks with parents cannot be expanded.

Setting `bootDiskCapacity` deadlocks the VM: disk promotion (which would remove
the parent) waits for power-on, and power-on waits for the resize. So the root
disk stays small and the space is a separate PVC. Keep bulky things in
`~/work` (a symlink to `/data/work`); Docker already uses `/data/docker`.

## Deploy

```sh
argocd app create se-jumpbox \
  --project default \
  --repo https://github.com/edric45/se-gitops.git \
  --revision main \
  --path supervisor/se-ns-argo/se-jumpbox \
  --dest-name supervisor-se-ns-argo \
  --dest-namespace se-ns-argo \
  --sync-option ServerSideApply=true
argocd app sync se-jumpbox
```

First boot installs everything; allow 10–15 minutes after the VM powers on.

## Getting in

```sh
kubectl --context 172.17.10.2 -n se-ns-argo get svc se-jumpbox    # the VIP
ssh jumpbox@<VIP> cat CREDENTIALS.txt                              # the password
ssh jumpbox@<VIP> cat /etc/motd                                    # what installed, disk usage
```

One generated password covers the KasmVNC login, code-server and `sudo`. It
is created on the VM at first boot, never in git — this repo is public.

The SSH key in `00-cloud-init.yaml` is `ss902385@broadcom.net`. Change it
there **before** the first sync; cloud-init only reads it once.

Both web ports use self-signed certificates.

## Changing it

cloud-init runs once. Editing `00-cloud-init.yaml` does nothing to a running
VM. Either re-run the setup on the VM (it keeps the existing password):

```sh
sudo /usr/local/sbin/jumpbox-setup.sh
```

or delete the VM (`Delete=false` means ArgoCD will not) and sync again. The
data PVC is also `Delete=false` and is only formatted when empty, so a
recreated VM gets `/data` back intact.
