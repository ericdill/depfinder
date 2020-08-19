$PROJECT = 'depfinder'
$ACTIVITIES = ['authors',
               'changelog',
               'tag',
               'push_tag',
               'ghrelease',
               'pypi',
               'conda_forge'
]

$TAG_TEMPLATE = $GHRELEASE_NAME = 'v$VERSION'

$CHANGELOG_FILENAME = 'CHANGELOG.rst'
$CHANGELOG_IGNORE = ['TEMPLATE']

$GITHUB_ORG = 'ericdill'
$GITHUB_REPO = 'depfinder'

$LICENSE_URL = 'https://github.com/{}/{}/blob/master/LICENSE'.format($GITHUB_ORG, $GITHUB_REPO)
