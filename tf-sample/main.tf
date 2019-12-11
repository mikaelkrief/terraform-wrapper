locals {
  common_app_settings = {
    "INSTRUMENTATIONKEY" = azurerm_application_insights.appinsight-app.instrumentation_key
  }
}

resource "azurerm_resource_group" "rg-app" {
  name     = "${var.resource_groupe_name}-${var.environement}"
  location = var.location
  tags = {
    ENV = var.environement
  }
}

resource "azurerm_app_service_plan" "plan-app" {
  name                = "${var.service_plan_name}-${var.environement}"
  location            = azurerm_resource_group.rg-app.location
  resource_group_name = azurerm_resource_group.rg-app.name

  sku {
    tier = "Standard"
    size = "S1"
  }

  tags = {
    ENV       = var.environement
    CreatedBy = var.createdby
  }
}

resource "azurerm_app_service" "app" {
  name                = "${var.app_name}-${var.environement}"
  location            = azurerm_resource_group.rg-app.location
  resource_group_name = azurerm_resource_group.rg-app.name
  app_service_plan_id = azurerm_app_service_plan.plan-app.id

  app_settings = merge(local.common_app_settings, var.custom_app_settings)

  site_config {
    dotnet_framework_version = "v4.0"
  }

  tags = {
    ENV       = var.environement
    CreatedBy = var.createdby
  }
}

resource "azurerm_application_insights" "appinsight-app" {
  name                = "${var.app_name}-${var.environement}"
  location            = azurerm_resource_group.rg-app.location
  resource_group_name = azurerm_resource_group.rg-app.name
  application_type    = "Web"

  tags = {
    ENV       = var.environement
    CreatedBy = var.createdby
    Test      = "ok2"
  }
}
