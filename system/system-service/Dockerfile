# ARG is used to pass some arguments to consecutive instructions and this is only command other than a comment can be used before FROM. We can see ARG usage in the below file and also we can pass that with the build command.
ARG NODE_VERSION=8.11-slim

# This is the first command in the Dockerfile. Without this, we can’t build an image. We can build the image just with this command. when we build just with FROM, we are actually taking the base image CMD whenever the image is instantiated.
FROM node:$NODE_VERSION

# LABEL is used to add some metadata to the image. if we use the same label as the base image and the most recent label value is applied.
LABEL "about"="This file is just am example to demonstarte the LABEL"

# ENV sets the environment variables for the subsequent instructions in the build stage. Consider the below example where we define the environment variable workdirectory and we used that later with $. There are two forms: single and multiple values
ENV workdirectory /home/bhargav
ENV workdirectory /etc/projectname

RUN mkdir /dockerexample

# VOLUME is used to create a mount point with the specified name. Following are the examples of Dockerfile and running instructions.
VOLUME /dockerexample

# COPY is used to copy files or directories from source host filesystem to a destination in the container file system. consider this example where we are copying package.json from our system to container file system. we can verify that while building with the RUN command ls -l.
COPY package.json .

RUN ls -ll && npm install

RUN useradd bhargav && mkdir -p $workdirectory && chown bhargav $workdirectory
    

# USER instruction sets the user name and optionally the user group to use when running the image and for any instructions that follow it in the Dockerfile
USER bhargav

# WORKDIR sets the working directory for all the consecutive commands. we can have multiple WORKDIR commands and will be appended with a relative path. Consider the following example where we have two WORKDIR commands leads to /usr/node/app
WORKDIR $workdirectory

ADD index.js .


# RUN executes the instructions in a new layer on top of the existing image and commit those layers and the resulted layer will be used for the next instructions in the Dockerfile. consider this example we are doing npm install and ls -l with one RUN to avoid any additional layers.
RUN ls -l


# EXPOSE is used as documentation for the port. This is just a communication between the person who builds the image and the person who runs the container. It doesn’t serve any other purpose other than documentation.
# For example, we have used port 3070 in the index.js file. So, we are letting people know who runs the container by using EXPOSE instruction in the Dockerfile.
EXPOSE 3070


# ENTRYPOINT is used as an executable for the container. Let’s look at the below example
# we are using ENTRYPOINT for executable command and using CMD command to pass some default commands to the executable.
ENTRYPOINT ["make"]

# CMD command is used to give the default commands when the image is instantiated, it doesn’t execute while build stage. There should be only one CMD per Dockerfile, you can list multiple but the last one will be executed.
# CMD ["node","-v"]
CMD ["start"]
