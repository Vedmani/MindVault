# Contributing to MindVault

Thank you for your interest in contributing to MindVault! This document provides guidelines and information for contributors.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Contributing Guidelines](#contributing-guidelines)
- [Pull Request Process](#pull-request-process)
- [Issue Reporting](#issue-reporting)
- [Development Workflow](#development-workflow)
- [Testing](#testing)
- [Documentation](#documentation)
- [Release Process](#release-process)

## Code of Conduct

MindVault is committed to providing a welcoming and inclusive environment for all contributors. Please read and follow our Code of Conduct:

### Our Pledge

- **Be respectful**: Treat all community members with respect and kindness
- **Be inclusive**: Welcome newcomers and diverse perspectives
- **Be collaborative**: Work together constructively
- **Be patient**: Help others learn and grow

### Unacceptable Behavior

- Harassment, discrimination, or offensive language
- Personal attacks or inflammatory comments
- Spam or self-promotion
- Sharing private information without consent

## Getting Started

### Prerequisites

- Python 3.12 or higher
- Git
- MongoDB (local or cloud)
- Basic knowledge of Python, AI/ML concepts, and web APIs

### First Steps

1. **Fork the repository** on GitHub
2. **Clone your fork** locally
3. **Set up development environment**
4. **Read the documentation** thoroughly
5. **Start with good first issues**

## Development Setup

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/mindvault.git
cd mindvault
```

### 2. Set Up Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
```

### 3. Install Dependencies

```bash
# Install in development mode
pip install -e ".[dev]"

# Install additional development tools
pip install pre-commit pytest pytest-cov black isort mypy
```

### 4. Set Up Pre-commit Hooks

```bash
pre-commit install
```

### 5. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your credentials
# Add your Twitter tokens, MongoDB URI, etc.
```

### 6. Initialize Database

```bash
# Start MongoDB (if local)
sudo systemctl start mongod

# Test database connection
python -c "from mindvault.core.config import settings; settings.validate_mongodb_connection()"
```

### 7. Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=mindvault --cov-report=html
```

## Contributing Guidelines

### Types of Contributions

We welcome various types of contributions:

1. **Bug Reports**: Help us identify and fix issues
2. **Feature Requests**: Suggest new functionality
3. **Code Contributions**: Implement features or fix bugs
4. **Documentation**: Improve or add documentation
5. **Testing**: Add or improve tests
6. **Performance**: Optimize existing code
7. **Refactoring**: Improve code structure and maintainability

### Contribution Areas

#### Core Features
- Twitter/X integration improvements
- AI processing enhancements
- Database optimization
- Browser automation features
- Workflow management

#### New Integrations
- Social media platforms
- Note-taking applications
- Cloud storage services
- Analytics tools
- Browser extensions

#### Developer Experience
- Testing infrastructure
- Development tools
- Documentation
- CI/CD improvements
- Error handling

### Finding Work

1. **Browse Issues**: Look for issues labeled:
   - `good first issue`: Great for newcomers
   - `help wanted`: Community input needed
   - `enhancement`: New feature requests
   - `bug`: Bug reports

2. **Check the Roadmap**: See our project roadmap for planned features

3. **Discuss Ideas**: Open an issue to discuss new ideas before implementing

## Pull Request Process

### 1. Create a Branch

```bash
# Create and switch to a new branch
git checkout -b feature/your-feature-name

# Or for bug fixes
git checkout -b fix/bug-description
```

### 2. Make Changes

- Follow the coding standards
- Write clear commit messages
- Add tests for new functionality
- Update documentation as needed

### 3. Commit Changes

```bash
# Stage changes
git add .

# Commit with clear message
git commit -m "Add feature: brief description

Detailed description of what was changed and why.
Closes #issue-number"
```

### 4. Push Changes

```bash
git push origin feature/your-feature-name
```

### 5. Create Pull Request

1. **Open a Pull Request** on GitHub
2. **Fill out the PR template** completely
3. **Link related issues** using "Closes #issue-number"
4. **Request review** from maintainers
5. **Address feedback** promptly

### PR Requirements

- [ ] Tests pass locally
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] No merge conflicts
- [ ] PR description is clear and complete

## Issue Reporting

### Bug Reports

Use the bug report template and include:

1. **Bug Description**: Clear, concise description
2. **Steps to Reproduce**: Detailed steps to recreate the issue
3. **Expected Behavior**: What you expected to happen
4. **Actual Behavior**: What actually happened
5. **Environment**: OS, Python version, dependencies
6. **Logs**: Relevant error messages or logs
7. **Additional Context**: Screenshots, configuration, etc.

### Feature Requests

Use the feature request template and include:

1. **Feature Description**: Clear description of the feature
2. **Use Case**: Why this feature is needed
3. **Proposed Solution**: How you envision it working
4. **Alternatives**: Alternative solutions considered
5. **Additional Context**: Examples, mockups, etc.

## Development Workflow

### Code Style

We follow these style guidelines:

- **PEP 8**: Python code style
- **Black**: Code formatting
- **isort**: Import sorting
- **Type hints**: Use throughout codebase
- **Docstrings**: Google-style docstrings

### Code Quality Tools

```bash
# Format code
black mindvault/

# Sort imports
isort mindvault/

# Type checking
mypy mindvault/

# Linting
flake8 mindvault/
```

### Commit Messages

Use conventional commit format:

```
type(scope): brief description

Detailed description of the change.

Closes #issue-number
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Test changes
- `chore`: Maintenance tasks

### Branch Naming

- `feature/description`: New features
- `fix/description`: Bug fixes
- `docs/description`: Documentation updates
- `refactor/description`: Code refactoring
- `test/description`: Test improvements

## Testing

### Test Structure

```
tests/
├── unit/           # Unit tests
├── integration/    # Integration tests
├── e2e/           # End-to-end tests
├── fixtures/      # Test data
└── conftest.py    # Pytest configuration
```

### Writing Tests

1. **Unit Tests**: Test individual functions and classes
2. **Integration Tests**: Test component interactions
3. **End-to-End Tests**: Test complete workflows

### Test Guidelines

- Use descriptive test names
- Test both success and failure cases
- Mock external dependencies
- Use fixtures for test data
- Aim for high code coverage

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/test_config.py

# Run with coverage
pytest --cov=mindvault

# Run specific test category
pytest -m "not slow"
```

## Documentation

### Documentation Types

1. **API Documentation**: Auto-generated from docstrings
2. **User Guides**: How-to guides for users
3. **Developer Docs**: Technical documentation
4. **Architecture Docs**: System design documentation

### Documentation Guidelines

- Use clear, concise language
- Include code examples
- Keep documentation up-to-date
- Use markdown format
- Include diagrams when helpful

### Building Documentation

```bash
# Install documentation dependencies
pip install -r docs/requirements.txt

# Build documentation
cd docs
make html

# Serve documentation locally
python -m http.server 8000
```

## Release Process

### Version Numbering

We use [Semantic Versioning](https://semver.org/):

- **MAJOR**: Incompatible API changes
- **MINOR**: New functionality (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Release Steps

1. **Update version** in `pyproject.toml`
2. **Update CHANGELOG.md** with release notes
3. **Create release branch**
4. **Run full test suite**
5. **Create GitHub release**
6. **Publish to PyPI**
7. **Update documentation**

### Release Criteria

- All tests pass
- Documentation updated
- Changelog updated
- No known critical bugs
- Feature complete for milestone

## Community Guidelines

### Communication Channels

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: General questions and discussions
- **Pull Requests**: Code reviews and discussions
- **Email**: Direct contact for sensitive issues

### Getting Help

1. **Read the documentation** first
2. **Search existing issues** for similar problems
3. **Ask in discussions** for general questions
4. **Open an issue** for bugs or feature requests
5. **Contact maintainers** for urgent issues

### Recognition

We recognize contributors through:

- **Contributors file**: All contributors listed
- **Release notes**: Major contributors mentioned
- **GitHub badges**: Contributor recognition
- **Community spotlight**: Highlighting contributions

## Development Tips

### Best Practices

1. **Start small**: Begin with small, focused changes
2. **Test thoroughly**: Ensure your changes work correctly
3. **Document changes**: Update relevant documentation
4. **Follow conventions**: Use established patterns
5. **Ask for help**: Don't hesitate to ask questions

### Common Pitfalls

- Not testing edge cases
- Forgetting to update documentation
- Making changes too large
- Not following code style
- Inadequate commit messages

### Debugging Tips

1. **Use logging**: Add detailed logging to your code
2. **Check configurations**: Verify environment variables
3. **Test locally**: Ensure changes work in your environment
4. **Use debugger**: Step through code when needed
5. **Read error messages**: Understand what went wrong

## Thank You

Thank you for contributing to MindVault! Your contributions help make this project better for everyone. Whether you're fixing a bug, adding a feature, or improving documentation, your efforts are appreciated.

---

**Questions?** Feel free to reach out:
- Open an issue for technical questions
- Start a discussion for general questions
- Contact maintainers for urgent matters

**Happy contributing!** 🚀