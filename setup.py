from setuptools import setup


def listify(filename):
    return filter(None, open(filename, 'r').read().strip('\n').split('\n'))

setup(
    name="distributex",
    version="0.1",
    url='http://github.com/calston/distributex',
    license='MIT',
    description="Distributex. A network mutex service for distributed"
                "environments.",
    long_description=open('README.md', 'r').read(),
    author='Colin Alston',
    author_email='colin.alston@gmail.com',
    packages=[
        "distributex",
        "twisted.plugins",
    ],
    package_data={
        'twisted.plugins': ['twisted/plugins/distributex_plugin.py']
    },
    include_package_data=True,
    install_requires=listify('requirements.txt'),
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Operating System :: POSIX',
        'Programming Language :: Python',
        'Topic :: System :: Clustering',
        'Topic :: System :: Distributed Computing',
    ],
)
