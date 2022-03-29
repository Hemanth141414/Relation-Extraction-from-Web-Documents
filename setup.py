setup(name='ISE',
      packages=['ise'],
      install_requires=[
          'google-api-python-client',
      ],
      entry_points={
          'console_scripts': [
              'run = __main__:main'
          ]
      },
)
