# Flask Microservice Builder


This python module builds a single Flask application from
a set of flask microservices from different repos. The builder expects
a standard way of writing the microservices with `microservices.json` input
 file and all the microservices
are aggregated and a release notes with deployed commit Ids is added to
the deployment.

**This project is under active development**

```
pip install git+https://github.com/invana/flask-microservice-builder#egg=flask_microservices_builder

```