# se-cluster-01 security samples

**Samples only. Nothing in this folder is applied.** The `cluster-se-cluster-01`
app reads only the files directly in `../` (it does not recurse) and syncs
manually, and no ApplicationSet watches this path. Each file says where and
how to apply it for a demo.

## The layers

| Layer | Folder | Applied on | What it shows |
|---|---|---|---|
| Node OS | [`os-lockdown/`](os-lockdown/cluster-snippet.yaml) | Supervisor (Cluster variables) | read-only `/usr`, FIPS, GRUB password, SSH banner |
| Node network | [`os-firewall/`](os-firewall/cluster-snippet.yaml) | Supervisor (Cluster variables) | extra allow rules on the node host firewall |
| Container runtime | [`apparmor/`](apparmor/) | Supervisor (profile + Cluster variable) and cluster (demo pods) | kernel-enforced lockdown per container, even for root |
| Admission policy | [`opa-gatekeeper/`](opa-gatekeeper/) | Supervisor (add-on) and cluster (policies) | approved registries, no `:latest`, required labels and limits; audit, then deny |
| Service mesh | [`istio-ambient/`](istio-ambient/) | cluster | mesh mTLS, identity-based L4 policy, L7 policy via waypoint, HTTPS at the edge |

Already on by default on VKS, with nothing to apply (verified on this cluster):
- **PodSecurity `restricted`** on every namespace (no privileged pods, host
  mounts or `Unconfined` AppArmor).
- **AppArmor `RuntimeDefault`**: every container runs under
  `cri-containerd.apparmor.d (enforce)` on Photon OS nodes whose kernel boots
  with `apparmor=1 security=apparmor`.

## What was verified (2026-09-29, nothing applied)

| Sample | Check | Result |
|---|---|---|
| `apparmor/01` AppArmorProfile | server dry-run on the Supervisor | accepted |
| AppArmor profile text | the node's own `apparmor_parser -Q` (parse only, never loaded) | parses |
| `apparmor/03` demo workloads | strict schema validation | valid |
| `os-lockdown` + `os-firewall` + `apparmor/02` | merged into a copy of the Cluster, server dry-run | fips, grub, sshd, apparmor, firewall accepted on v1.35.6. **Immutability needs v1.36.0+ and Photon-pinned pools**: accepted on v1.36.2 with the annotations |
| GRUB password Secret | server dry-run | accepted (the value is a placeholder) |
| `opa-gatekeeper/00` add-on | values checker + server dry-run | valid |
| Rego in `opa-gatekeeper/10` | `opa check --v1-compatible` (OPA 1.21) | all 4 compile |
| `opa-gatekeeper/20`, `30` | YAML / strict schema (Gatekeeper not installed) | valid |
| `istio-ambient/*` | server dry-run in the cluster | all 9 objects accepted |

**Not yet exercised on a live cluster:** loading the custom AppArmor profile
(including whether that replaces nodes), the Gatekeeper policies' runtime
behaviour, the waypoint, the HTTPS listener, and the node firewall rules.

## Findings worth telling in a workshop

- **Read-only `/usr` has a documented gap:** VMware's own description says it
  does not stop a privileged pod (root with CAP_SYS_ADMIN) from remounting it.
  PodSecurity and AppArmor close that gap. That's the defense-in-depth story.
- **Read-only `/usr` needs Kubernetes 1.36.0+**, and at cluster level every
  pool must be pinned to Photon (`run.tanzu.vmware.com/resolve-os-image:
  os-name=photon`). VKS's admission webhook enforces both.
- **Istio's generated proxies (Gateways and waypoints) don't meet PodSecurity
  `restricted`** (no `seccompProfile`), so their namespaces need `baseline`.
- **AppArmor profiles are immutable objects:** a new version means a new
  object and a Cluster change.
