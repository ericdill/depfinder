from setuptools import setup


setup(
    name="depfinder",
    use_scm_version={
        "write_to": "depfinder/_version.py",
        "write_to_template": '__version__ = "{version}"',
        "tag_regex": r"^(?P<prefix>v)?(?P<version>[^\+]+)(?P<suffix>.*)?$",
    },
)
