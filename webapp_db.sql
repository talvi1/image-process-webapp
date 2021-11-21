DROP SCHEMA IF EXISTS `webapp`;

CREATE SCHEMA IF NOT EXISTS `webapp` DEFAULT CHARACTER SET utf8 ;
USE `webapp`;

DROP TABLE IF EXISTS `webapp`.`users` ;

CREATE TABLE IF NOT EXISTS `webapp`.`users` (
  `ID` INT NOT NULL AUTO_INCREMENT,
  `username` VARCHAR(50) NOT NULL,
  `salt` BINARY(50) NOT NULL,
  `password` BINARY(60) NOT NULL,
  `email` VARCHAR(50),
  `admin` BOOLEAN, 
  PRIMARY KEY (`ID`)
)
ENGINE = InnoDB;

DROP TABLE IF EXISTS `webapp`.`recover`;

CREATE TABLE IF NOT EXISTS `webapp`.`recover` (
    `ID` INT NOT NULL AUTO_INCREMENT,
    `username` VARCHAR(50) NOT NULL,
    `recoverykey` BINARY(50) NOT NULL,
    PRIMARY KEY (`ID`)
)
ENGINE = InnoDB;

DROP TABLE IF EXISTS `webapp`.`images`;

CREATE TABLE IF NOT EXISTS `webapp`.`images`(
        `ID` INT NOT NULL AUTO_INCREMENT,
        `username` VARCHAR(50) NOT NULL,
        `image` VARCHAR(50) NOT NULL,
        PRIMARY KEY (`ID`)
)
ENGINE = InnoDB;

