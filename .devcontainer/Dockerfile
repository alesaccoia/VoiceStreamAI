FROM ghcr.io/shoppal-ai/llm-base

ARG HTTP_PROXY
ARG HTTPS_PROXY

RUN apt update && apt install -y zsh curl git sudo wget libsndfile1

# # install python environment
# RUN apt install -y python3.8-dev python3-pip 
# RUN update-alternatives --install /usr/bin/pthon python /usr/bin/python3.10 1 
RUN apt install -y python3.10-venv

ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME

RUN usermod -aG sudo $USERNAME
RUN echo 'vscode ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

USER $USERNAME

RUN cd ~ && wget https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh && sh install.sh

RUN python3 -m venv ~/venv
RUN echo "source ~/venv/bin/activate" >> ~/.zshrc

# Set Python path in the virtual environment.
RUN echo "export PYTHONPATH=\$PYTHONPATH:/workspace" >> ~/.zshrc
RUN /bin/zsh ~/.zshrc

ENV DEBIAN_FRONTEND=dialog

