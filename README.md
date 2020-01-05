[![Coverage Status](https://coveralls.io/repos/github/dacrands/s3-upload-backend/badge.svg?branch=master)](https://coveralls.io/github/dacrands/s3-upload-backend?branch=master)
[![Build Status](https://travis-ci.org/dacrands/s3-upload-backend.svg?branch=master)](https://travis-ci.org/dacrands/s3-upload-backend)

# Just Files API
Amazon S3 API with user-authentication and SendGrid email-support built with Flask.
 

## Getting Started

To run this application you will need Python 3 installed on your machine and accounts for two third-party services:
- [Amazon S3](https://aws.amazon.com/s3/)
- [SendGrid](https://sendgrid.com/)

### AWS Configuration
First, configure your AWS credentials on your machine. You may do so using the AWS CLI or by editing the AWS credentials file yourself.

- [Installing the AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-install.html)
- [Configuring the AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html)
- [Setup AWS Credentials](https://docs.aws.amazon.com/sdk-for-java/v1/developer-guide/setup-credentials.html) *(Instructions for those not using AWS CLI)*

Once your AWS credentials are configured, it is time to create a virtual environment for the app.

### Create an env

Clone the repository (https://github.com/dacrands/s3-upload-backend.git) and cd into it. 

```
~ $ git clone https://github.com/dacrands/s3-upload-backend.git
~ $ cd s3-upload-backend
```
We will use *venv* to create our environment.
- [venv documentation](https://docs.python.org/3/library/venv.html#)

Once in your repository, create a virtual environment using `venv` then activate the environment:

**Linux/Mac**
```
~/s3-upload-backend $ python3 -m venv venv
~/s3-upload-backend $ source venv/bin/activate
(venv) ~/s3-upload-backend $ 
```

**Windows**

```
C:\s3-upload-backend> python3 -m venv venv
C:\s3-upload-backend> venv\Scripts\activate.bat
(venv) C:\s3-upload-backend> 
```

Now that our environment is activated, let's install our app's dependencies.

### Install your requirements

With your environment active, run the following command in your app's root directory (viz., the directory that contains the *requirements.txt* file).

```
pip install -r requirements.txt 
```

### Config

For development you can leave the *SECRET_KEY* and *SQLALCHEMY_DATABASE_URI* variables as their defaults. In production, however, those will need be set to their respective values.

Run the following commands to configure your S3 Bucket and SendGrid API key. Windows users will use `set` instead `export`:

```
export S3_BUCKET=<your_bucket>
export SENDGRID_API_KEYT=<your_api_key>
``` 

Given our app is properly figured, it is time to run the application.

### Run the app

Before we can run the app, we need to tell flask the name of the file it will use to create our app. To do this, set the environment variable *FLASK_APP* to *run.py*:

```
export FLASK_APP=run.py
```

To run your app in debug mode, set *FLASK_DEBUG* to 1. For a production build, set *FLASK_DEBUG* to 0, which is the default value.

```
export FLASK_DEBUG=1
```


Then run the application:

```
flask run
```

If all goes well, you should be able to visit the API at *localhost:5000*.

## Author
David Crandall

