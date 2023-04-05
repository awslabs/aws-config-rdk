from setuptools import find_packages, setup

import rdk as this_pkg

setup(
    name=this_pkg.DIST_NAME,
    version=this_pkg.VERSION,
    description=this_pkg.DESCRIPTION,
    long_description=this_pkg.DESCRIPTION,
    long_description_content_type="text/plain",
    url=this_pkg.URL,
    license="Apache-2.0",
    author=this_pkg.MAINTAINER,
    author_email=this_pkg.MAINTAINER_EMAIL,
    maintainer=this_pkg.MAINTAINER,
    maintainer_email=this_pkg.MAINTAINER_EMAIL,
    python_requires=">=3.8",
    zip_safe=False,
    packages=find_packages(include=[f"{this_pkg.NAME}", f"{this_pkg.NAME}.*"]),
    package_data={
        this_pkg.NAME: ["py.typed"],
    },
    install_requires=[
        "aiofiles<1",
        # "aws-cdk<2",
        "aws-cdk-lib>=2",
        "constructs>=10,<11",
        # "boto3>=1,<2",
        # "c1-p13rlib>=2,<3",
        # "c7n",
        "colorlog>=4,<5",
        "httpx<1",
        "mergedeep>=1,<2",
        "pytest>=6,<7",
        "semver>=2,<3",
    ],
    entry_points={
        "console_scripts": [
            f"{this_pkg.CLI_NAME}={this_pkg.NAME}.cli.main:main",
        ],
        "pytest11": [f"pytest_{this_pkg.NAME}={this_pkg.NAME}.pytest.fixture"],
    },
)
