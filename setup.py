# setup.py
from setuptools import setup, find_packages

setup(
    name='timefolio-bot',
    version='0.1.0',
    description='Timefolio Mock Investment API Wrapper',
    author='Your Name',
    packages=find_packages(), # timefolio 폴더를 자동으로 찾아줍니다.
    install_requires=[
        'requests', # 이 라이브러리가 돌아가기 위해 필요한 패키지들
    ],
)