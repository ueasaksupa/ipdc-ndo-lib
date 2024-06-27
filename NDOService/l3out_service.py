from .core.configurations import *
from .core.ndo_connector import NDOTemplate
from NDOService.core.service_parameters import *


def create(srvParams: L3OutServiceParameters):
    """
    For create L2 service
    """
    if not isinstance(srvParams, L3OutServiceParameters):
        raise ValueError("srvParams must be instance of L3OutServiceParameters class.")

    ndo = NDOTemplate(
        srvParams.connection.host,
        srvParams.connection.username,
        srvParams.connection.password,
        srvParams.connection.port,
    )
    # create Tenant
    tenant = ndo.create_tenant(srvParams.tenant_name, srvParams.tenant_sites)
    # get schema by name if schema was not been created before, It will be created automatically
    schema = ndo.create_schema(srvParams.schema_name)

    # ----- CREATE TENANT POLICY TEMPLATE ------
    tPolicy = srvParams.tenantPolTemplate
    ndo.create_tenant_policies_template(tPolicy.name, srvParams.tenant_sites, srvParams.tenant_name)
    ndo.add_route_map_policy_under_template(tPolicy.name, tPolicy.routemapConfig)

    # ----- CREATE TEMPLATE ------
    for template in srvParams.templates:
        if template.name is not None:
            # prepare empty VRF template
            ndo.create_template(schema, template.name, tenant["id"])
            # associate site to template
            ndo.add_site_to_template(schema, template.name, template.associatedSites)
            # update schema
            schema = ndo.save_schema(schema)

        # ----- CREATE VRF UNDER TEMPLATE ------
        if isinstance(template, VRFTemplate):
            vrf_config = VrfConfig() if template.vrfConfig is None else template.vrfConfig
            # create filter under template
            ndo.create_filter_under_template(schema, template.name, template.filter_name)
            # create contract under template
            ndo.create_contract_under_template(schema, template.name, template.contract_name, template.filter_name)
            # create VRF under template
            ndo.create_vrf_under_template(schema, template.name, template.vrf_name, template.contract_name, vrf_config)
            # update schema
            schema = ndo.save_schema(schema)
            # ----- CREATE L3OUT TEMPLATE ------
            for l3outTemplate in srvParams.l3outTemplatePerSite:
                ndo.create_l3out_template(l3outTemplate.name, l3outTemplate.site, srvParams.tenant_name)
                ndo.add_l3out_under_template(l3outTemplate.name, l3outTemplate.l3outConfig)

        # ----- CREATE BD, ANP, EPG, ExternalEPG UNDER TEMPLATE ------
        if isinstance(template, MultiEPGTemplate):
            # create External EPG
            if template.externalEPG is not None:
                eepg = template.externalEPG
                ndo.create_ext_epg_under_template(
                    schema, template.name, eepg.name, eepg.linkedVrfName, eepg.linkedVrfTemplate, eepg.associatedL3Out
                )

            # create Bridge-Domain under template
            for bd in template.bds:
                bd_config = BridgeDomainConfig() if bd.bdConfig is None else bd.bdConfig
                ndo.create_bridge_domain_under_template(
                    schema,
                    bd.linkedVrfTemplate,
                    template.name,
                    bd.linkedVrfName,
                    bd.name,
                    bd_config,
                )
                # create Application Profile under template
                anp = ndo.create_anp_under_template(schema, template.name, bd.anp_name)
                # create EPG under ANP
                ndo.create_epg_under_template(schema, anp, template.name, bd.name, bd.epg.name)

                # update schema
                schema = ndo.save_schema(schema)

                # ----- ADD PHYSICAL PORT FOR EACH ENDPOINT PER SITE ------
                # add physical domain and device port to EPG per site
                for siteInfo in bd.epg.endpointPerSite:
                    ndo.add_phy_domain_to_epg(
                        schema,
                        template.name,
                        bd.anp_name,
                        bd.epg.name,
                        siteInfo.epg_phy_domain,
                        siteInfo.name,
                    )
                    ndo.add_static_port_to_epg(
                        schema,
                        template.name,
                        bd.anp_name,
                        bd.epg.name,
                        siteInfo.name,
                        siteInfo.endpoints,
                    )
                # update schema
                schema = ndo.save_schema(schema)


if __name__ == "__main__":
    """
    FOR TEST
    """
