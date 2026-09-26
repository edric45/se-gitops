#!/bin/sh
# Registers the Supervisor with ArgoCD, scoped to the se-ns-argo namespace only.
#
#   ./bootstrap/15-register-supervisor.sh
#
# Run after 10-argocd.yaml is Ready. Safe to run step by step by hand instead.
set -eu

# 1. A kube context scoped to se-ns-argo. `argocd cluster add` takes a context
#    name, and the Supervisor login only creates one per cluster namespace.
kubectl config set-context se-ns-argo \
  --cluster=172.17.10.2 \
  --user=wcp:172.17.10.2:administrator@wkld01.vks.lab \
  --namespace=se-ns-argo

# 2. Log the argocd CLI into OUR instance. The CLI may also hold a login for
#    argocd.mgmt.vks.lab, which is a different ArgoCD -- hence --name.
#    Prompts for the admin password. The admin password has been changed, so
#    argocd-initial-admin-secret no longer holds it.
argocd login 172.17.10.26 --username admin --insecure --name se-ns-argo

# 3. Register the Supervisor.
#    --namespace         ArgoCD may only deploy into se-ns-argo (RoleBinding,
#                        not ClusterRoleBinding).
#    --system-namespace  where the argocd-manager SA goes. The default is
#                        kube-system, which is off limits on a Supervisor.
argocd cluster add se-ns-argo \
  --name supervisor-se-ns-argo \
  --namespace se-ns-argo \
  --system-namespace se-ns-argo \
  --yes

# 4. Verify. STATUS reads Unknown until an Application targets the cluster.
argocd cluster list
kubectl --context se-ns-argo auth can-i create deployments -n se-ns-argo \
  --as=system:serviceaccount:se-ns-argo:argocd-manager    # yes
kubectl --context se-ns-argo auth can-i create deployments -n se-namespace \
  --as=system:serviceaccount:se-ns-argo:argocd-manager || true  # no
