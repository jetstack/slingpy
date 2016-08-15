from setuptools import setup, find_packages


with open("README.md") as fp:
    long_description = fp.read()


setup(
    name='slingpy',
    version="0.1.0",
    description='Slingshot helper modules',
    url='http://github.com/jetstack/slingpy',
    author='Christian Simon',
    author_email='christian@jetstack.io',
    license="Apache",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
    ],
    zip_safe=False,
    packages=find_packages(),
    install_requires=[
        "PyYAML",
    ],
)
