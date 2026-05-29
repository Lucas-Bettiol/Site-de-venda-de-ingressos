-- MySQL Workbench Forward Engineering

SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;
SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION';

-- -----------------------------------------------------
-- Schema DB_Ingressos
-- -----------------------------------------------------

-- -----------------------------------------------------
-- Schema DB_Ingressos
-- -----------------------------------------------------
CREATE SCHEMA IF NOT EXISTS `DB_Ingressos` DEFAULT CHARACTER SET utf8 ;
USE `DB_Ingressos` ;

-- -----------------------------------------------------
-- Table `DB_Ingressos`.`Usuarios`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `DB_Ingressos`.`Usuarios` (
  `Usuario_ID` INT NOT NULL AUTO_INCREMENT,
  `Ususario_Nome` VARCHAR(100) NOT NULL,
  `Usuario_Email` VARCHAR(100) NOT NULL,
  `Usuario_Senha` VARCHAR(20) NOT NULL,
  `Usuario_Admin` TINYINT NOT NULL DEFAULT 0,
  PRIMARY KEY (`Usuario_ID`))
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `DB_Ingressos`.`Ingressos`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `DB_Ingressos`.`Ingressos` (
  `Ingresso_ID` INT NOT NULL AUTO_INCREMENT,
  `Ingresso_Nome` VARCHAR(200) NOT NULL,
  `Ingresso_Data` DATE NOT NULL,
  `Ingresso_Valor` INT NOT NULL,
  `Ingresso_Quantidade` INT NOT NULL,
  PRIMARY KEY (`Ingresso_ID`))
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `DB_Ingressos`.`Pedidos`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `DB_Ingressos`.`Pedidos` (
  `Pedido_ID` INT NOT NULL AUTO_INCREMENT,
  `Usuario_ID` INT NOT NULL,
  `Ingresso_ID` INT NOT NULL,
  `Pedido_Tipo_Pag` VARCHAR(45) NOT NULL,
  `Pedido_QNT_Ingressos` INT NOT NULL,
  `Pedido_Valor` INT NOT NULL,
  PRIMARY KEY (`Pedido_ID`),
  INDEX `Usuario_ID_idx` (`Usuario_ID` ASC) VISIBLE,
  INDEX `Ingresso_ID_idx` (`Ingresso_ID` ASC) VISIBLE,
  CONSTRAINT `Usuario_ID_FK`
    FOREIGN KEY (`Usuario_ID`)
    REFERENCES `DB_Ingressos`.`Usuarios` (`Usuario_ID`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION,
  CONSTRAINT `Ingresso_ID_FK`
    FOREIGN KEY (`Ingresso_ID`)
    REFERENCES `DB_Ingressos`.`Ingressos` (`Ingresso_ID`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB;


SET SQL_MODE=@OLD_SQL_MODE;
SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;
SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS;
