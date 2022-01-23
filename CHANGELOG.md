# Changelog

All notable changes to the project will be documented in this file.

## [2.3.9] - 23JAN22
### Added
- CHANGELOG
- Ability to get the high score from the active event(s)
- Ability to get the high auto score from the active event(s)
- Ability to get the season high

### Changed
- Removed changelog from README and moved it to CHANGELOG file.
- Added vPing Command to README

### Fixed
- Fixed issue when trying to iterate over all active events.

## [2.3.8] - 23JAN22
- Configured logging to stdout

## [2.3.7] - 22JAN22
### Added
- Added vPing to test Voice

## [2.3.6] - 22JAN22
### Fixed
- Fixed Voice issues by utilizing FFmpegPCMAudioGTTS. 

### Security
- Updated requirements.txt

## [2.3.5] - 22JAN22
### Added
- Added FTC Event GET command to report what events are currently being monitored.

## [2.3.4] - 22JAN22
### Fixed
- Troubleshooting Voice issues.

## [2.3.3] - 16JAN22
### Added
- Added counter to display progress when adding an event.

## [2.3.2] - 16JAN22
### Changed
- Updated testBuild.sh

### Fixed
- Fixed issues. 

## [2.3.1] - 15JAN22
### Security
- Updated requirements to latest

## [2.3.0] - 15JAN22
### Added
- Added error handling to SendTTS function.

### Changed
- Updated for 2022 FRC Season and v3 API. 

## [2.2.3] - 11DEC21
### Added
- Added ability to stop all monitored events at once.

## [2.2.2] - 11DEC21
### Added
- Added loging to avoid rate limiting.

## [2.2.1] - 11DEC21
### Added
- Added logging for websocket and FTCTeam Instances.

## [2.2.0] - 4DEC21
### Added
- Added inserting rankings to mySQL server on comit. 

### Changed
- README to add Ping Command

## [2.1.1] - 30NOV21
### Added
- Added Ping Command

## [2.1.0] - 30NOV21
### Added
- Support for Elimination, Semi-Final, and Finals matches. 

### Fixed
- Fixed issue with TTS. 
- Began improving get API key command.

## [2.0.0] - 24OCT21
### Changed
- Updated bot to support 2022 FTC season.

## [1.1.4] - 22FEB21
### Added
- Added aliases for frcteam and ftcteam commands.

## [1.1.3] - 16FEB21
### Changed
- Modifed react role. If user already had role remove it. If user is member of Auto Assigned role remove their reaction and do nothing.

## [1.1.2] - 16FEB21
### Added
- Added ability to assign role to user when they react to a specific message.

## [1.1.1] - 14FEB21
### Added
- Added argument to event start for the event name. This gets passed to the voice announcments.

## [1.1.0] - 7FEB21
### Added
- Added voice announcments for match status (Start, Post, Abort).

## [1.0.8] - 7FEB21
### Changed
- Updated example.env

### Fixed
- Fixed Match Results to post only to Match Results channel

## [1.0.7] - 7FEB21
### Added
- BOTMATCHRESULTCHANNELS ENV Variable

### Changed
- Configured match results to only send to that channel
- Configured bot to allow team commands from all but that channel.

## [1.0.7] - 31JAN21
### Added
- Saving match results to mySQL server on comit
- Ability to set multiple admin and production channels

### Fixed
- Fixed issue with websocket

### Security
- Updated base image version
- Updated requirements to latest

## [1.0.6] - 13NOV20
### Changed
- Changed Admin Role to ENV variable

## [1.0.1] - 2NOV20
### Added
- Auto Assign new users the ""Needs Registration"" Role
- Clear/Sweep Command

### Changed
- Modified bot to also listen for all commands on the Admin channel as well

## [1.0] - 1NOV20
- Initial Release