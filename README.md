# Cloud solution for a toy kubernetes assignment
Clone a github repo and upload its files in parallel to a GCP bucket ([full description](problem_statement/SI_cloud_test.pdf))

## Solution (using Google Cloud Platform)
1. Make a [free GCP account](https://youtu.be/P2ADJdk5mYo) and project.
2. Install [gcloud CLI](https://cloud.google.com/sdk/docs/install); configure it for the project and enable Compute Engine API, Cloud Deployment Manager.
3. Create a service account for Kubernetes Engine Admin; generate and save auth key in console UI or with cli:
    ```gcloud projects add-iam-policy-binding ${KF_PROJECT} --member=${TYPE}:${EMAIL} --role=roles/{iap.httpsResourceAccessor,container.clusterViewer,viewer} --condition=None```
4. Create a cluster with appropriate [OAuth scope](https://cloud.google.com/compute/docs/access/service-accounts#accesscopesiam) (check [machine types](https://cloud.google.com/compute/docs/general-purpose-machines) to avoid unnecessary billing).
    ```gcloud container clusters create test_pipeline --zone europe-west4-c --machine-type e2-standard-2 --scopes cloud-platform```
5. Create nodepool for the cluster.
    ```gcloud container node-pools update default-pool --cluster test_pipeline --min-nodes 0 --num-nodes 0 --max-nodes 4 --enable-autoscaling --preemptible```
6. Install [kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl-linux/) and configure it to talk to GC ([doc](https://cloud.google.com/kubernetes-engine/docs/how-to/cluster-access-for-kubectl#apt_1))
7. Deploy kubeflow pipelines ([doc](https://www.kubeflow.org/docs/components/pipelines/installation/standalone-deployment/))
8. Create a storage bucket, add permissions for service account as both Storage Bucket and Objects Owner.
9. Create a docker image with appropriate gcloud config and ssh keys ([Dockerfile](solution/Dockerfile), *replace project name inside*)
10. Install KF pipelines SDK ([doc](https://www.kubeflow.org/docs/components/pipelines/sdk/install-sdk/))
11. Write a [solution pipeline](solution/si_testproject_pipeline.py), compile with KF DSL compiler into a yaml.
12. Upload the pipeline.yaml to KF pipelines dashboard and run an experiment.
    ![Representative pipeline DAG](solution/sample_test_run.png)
