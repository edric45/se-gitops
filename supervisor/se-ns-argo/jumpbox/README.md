# jumpbox

An Ubuntu 24.04 desktop VM in `se-ns-argo`, reachable from a browser through an
Avi VIP. For debugging the lab: it sits in the same VPC as the cluster nodes.

| | |
|---|---|
| Desktop in the browser | `https://<VIP>/` — KasmVNC, XFCE, Chrome, VS Code, terminal |
| VS Code in the browser | `https://<VIP>:8443/` — code-server |
| SSH | `ssh jumpbox@<VIP>` — key only |
| Size | `best-effort-xlarge` (4 vCPU / 32Gi), 100Gi disk |

Tools: `kubectl` + `kubectl-vsphere` (from the Supervisor), `vcf` CLI v9.0.2,
`argocd` (from our ArgoCD server), `k9s`, `helm`, `kubectx`/`kubens`, `stern`,
`yq`, `velero`, `mc`, `istioctl`, `govc`, Docker, git, and the usual network
tools (`tcpdump`, `nmap`, `mtr`, `dig`, `iperf3`, `nc`, `socat`, ...).

## Deploy

```sh
argocd app create jumpbox \
  --project default \
  --repo https://github.com/edric45/se-gitops.git \
  --revision main \
  --path supervisor/se-ns-argo/jumpbox \
  --dest-name supervisor-se-ns-argo \
  --dest-namespace se-ns-argo \
  --sync-option ServerSideApply=true
argocd app sync jumpbox
```

First boot installs everything; allow 10–15 minutes after the VM powers on.

## Getting in

```sh
kubectl --context 172.17.10.2 -n se-ns-argo get svc jumpbox       # the VIP
ssh jumpbox@<VIP> cat CREDENTIALS.txt                              # the password
ssh jumpbox@<VIP> cat /etc/motd                                    # what installed, what failed
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

or delete the VM (`Delete=false` means ArgoCD will not) and sync again.
