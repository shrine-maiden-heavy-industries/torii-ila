# SPDX-License-Identifier: BSD-3-Clause

import shutil
from os             import getenv
from pathlib        import Path
from setuptools_scm import ScmVersion, get_version

import nox
from nox.sessions   import Session

ROOT_DIR  = Path(__file__).parent

BUILD_DIR = (ROOT_DIR  / 'build')
CNTRB_DIR = (ROOT_DIR  / 'contrib')
DOCS_DIR  = (ROOT_DIR  / 'docs')
DIST_DIR  = (BUILD_DIR / 'dist')

IN_CI           = getenv('GITHUB_WORKSPACE') is not None
ENABLE_COVERAGE = IN_CI or (getenv('TORII_TEST_COVERAGE') is not None)

# Default sessions to run
nox.options.sessions = (
	'test',
	'lint',
	'typecheck'
)

def torii_ila_version() -> str:
	def scheme(version: ScmVersion) -> str:
		if version.tag and not version.distance:
			return version.format_with('')
		else:
			return version.format_choice('+{node}', '+{node}.dirty')

	return get_version(
		root           = str(ROOT_DIR),
		version_scheme = 'guess-next-dev',
		local_scheme   = scheme,
		relative_to    = __file__
	)

@nox.session(reuse_venv = True)
def test(session: Session) -> None:
	out_dir = (BUILD_DIR / 'tests')
	out_dir.mkdir(parents = True, exist_ok = True)

	unitest_args = ('-m', 'unittest', 'discover', '-v', '-s', str(ROOT_DIR))

	session.install('.')
	if ENABLE_COVERAGE:
		session.log('Coverage support enabled')
		session.install('coverage')
		coverage_args = (
			'-m', 'coverage', 'run',
			f'--rcfile={CNTRB_DIR / "coveragerc"}'
		)
	else:
		coverage_args = ()

	session.chdir(str(out_dir))
	session.run(
		'python', *coverage_args, *unitest_args, *session.posargs
	)
	if ENABLE_COVERAGE:
		session.run(
			'python', '-m', 'coverage', 'xml',
			f'--rcfile={CNTRB_DIR / "coveragerc"}'
		)

@nox.session
def docs(session: Session) -> None:
	out_dir = (BUILD_DIR / 'docs')
	shutil.rmtree(out_dir, ignore_errors = True)
	session.install('-r', str(DOCS_DIR / 'requirements.txt'))
	session.install('.[usb,serial]')
	session.run('sphinx-build', '-b', 'html', str(DOCS_DIR), str(out_dir))

@nox.session
def docs_linkcheck(session: Session) -> None:
	out_dir = (BUILD_DIR / 'docs-linkcheck')
	shutil.rmtree(out_dir, ignore_errors = True)
	session.install('-r', str(DOCS_DIR / 'requirements.txt'))
	session.install('.')
	session.run('sphinx-build', '-b', 'linkcheck', str(DOCS_DIR), str(out_dir))

@nox.session
def typecheck(session: Session) -> None:
	out_dir = (BUILD_DIR / 'mypy')
	out_dir.mkdir(parents = True, exist_ok = True)

	session.install('mypy')
	session.install('lxml')
	session.install('.')
	session.run(
		'mypy', '--non-interactive', '--install-types', '--pretty',
		'--cache-dir', str((out_dir / '.mypy-cache').resolve()),
		'--config-file', str((CNTRB_DIR / '.mypy.ini').resolve()),
		'-p', 'torii_ila', '--html-report', str(out_dir.resolve())
	)

@nox.session
def lint(session: Session) -> None:
	session.install('flake8')
	session.run(
		'flake8', '--config', str((CNTRB_DIR / '.flake8').resolve()),
		'./torii_ila'
	)
	session.run(
		'flake8', '--config', str((CNTRB_DIR / '.flake8').resolve()),
		'./tests'
	)
	session.run(
		'flake8', '--config', str((CNTRB_DIR / '.flake8').resolve()),
		'./examples'
	)

@nox.session
def dist(session: Session) -> None:
	session.install('build')
	session.run(
		'python', '-m', 'build',
		'-o', str(DIST_DIR)
	)

@nox.session
def upload(session: Session) -> None:
	session.install('twine')
	dist(session)
	session.log(f'Uploading torii_ila-{torii_ila_version()} to PyPi')
	session.run(
		'python', '-m', 'twine', 'upload',
		f'{DIST_DIR}/torii_ila-{torii_ila_version()}.tar.gz',
		f'{DIST_DIR}/torii_ila-{torii_ila_version()}-py3-*.whl'
	)
