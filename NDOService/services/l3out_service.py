from ..core.configurations import *
from ..core.ndo_connector import NDOTemplate
from ..core.service_parameters import *


def create_service(
    ndo: NDOTemplate,
    srvParams: ServiceL3OutParameters,
    allowPushToUnSyncSchema: bool = True,
    strictPortCheck: bool = False,
    replace: bool = False,
):
    """
    For create L3Out service
    """
    if not isinstance(srvParams, ServiceL3OutParameters):
        raise ValueError("srvParams must be instance of ServiceL3OutParameters class.")

    # prepare sites for tenant creation
    allSiteList: list[str] = list(map(lambda s: s["name"], ndo.get_all_sites()))
    tenant_sites = allSiteList if srvParams.tenant_sites is None else srvParams.tenant_sites
    # create Tenant
    tenant = ndo.create_tenant(srvParams.tenant_name, tenant_sites)
    # get schema by name if schema was not been created before, It will be created automatically
    schema = ndo.create_schema(srvParams.schema_name)
    # check schema sync state from NDO
    if not allowPushToUnSyncSchema and not ndo.isSchemaStateSync(schema=schema):
        print(f"#### STOP, BECAUSE SCHEMA {schema['displayName']} is OUT OF SYNC ####")
        return

    # ----- CREATE TENANT POLICY TEMPLATE ------
    tPolicy = srvParams.tenantPolTemplates
    for pol in tPolicy:
        ndo.create_tenant_policies_template(pol.name, [pol.site], srvParams.tenant_name)
        ndo.add_route_map_policy_under_template(
            pol.name, pol.routemapConfig, operation="replace" if replace else "add"
        )

    # ----- CREATE TEMPLATE ------
    for template in srvParams.templates:
        if template.name is not None:
            # prepare empty VRF template
            ndo.create_template(schema, template.name, tenant["id"])
            # associate site to template
            template_sites = allSiteList if template.associatedSites == "_all_" else template.associatedSites
            ndo.add_site_to_template(schema, template.name, template_sites)

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
                ndo.add_l3out_under_template(
                    l3outTemplate.name, l3outTemplate.l3outConfig, operation="replace" if replace else None
                )

        # ----- CREATE BD, ANP, EPG, ExternalEPG UNDER TEMPLATE ------
        if isinstance(template, EPGsTemplate):
            # create External EPG
            if template.externalEPG is not None:
                eepg = template.externalEPG
                ndo.create_ext_epg_under_template(
                    schema=schema,
                    template_name=template.name,
                    epg_name=eepg.name,
                    linked_vrf_schema=eepg.linkedVrfSchema,
                    linked_vrf_template=eepg.linkedVrfTemplate,
                    linked_vrf_name=eepg.linkedVrfName,
                    l3outToSiteInfo=eepg.associatedL3Out,
                    eepg_subnets=eepg.subnets,
                    replace=replace,
                )

            # create Bridge-Domain under template
            for bd in template.bds:
                bd_config = bd.bdConfig
                ndo.create_bridge_domain_under_template(
                    schema=schema,
                    template_name=template.name,
                    linked_vrf_schema=bd.linkedVrfSchema,
                    linked_vrf_template=bd.linkedVrfTemplate,
                    linked_vrf_name=bd.linkedVrfName,
                    bd_name=bd.name,
                    bd_config=bd_config,
                    replace=replace,
                )
                # create Application Profile under template
                anp = ndo.create_anp_under_template(schema, template.name, bd.anp_name)
                # create EPG under ANP
                epg_config = EPGConfig(
                    epg_desc=bd.epg.epg_description,
                    linked_template=template.name,
                    linked_bd=bd.name,
                    proxyArp=bd.epg.proxyArp,
                    mCastSource=bd.epg.mCastSource,
                )
                ndo.create_epg_under_template(schema, anp, bd.epg.name, epg_config)
                # update schema
                schema = ndo.save_schema(schema)

                # ----- ADD PHYSICAL PORT FOR EACH ENDPOINT PER SITE ------
                # add physical domain and device port to EPG per site
                for siteInfo in bd.epg.staticPortPerSite:
                    ndo.add_phy_domain_to_epg(
                        schema,
                        template.name,
                        bd.anp_name,
                        bd.epg.name,
                        siteInfo.epg_phy_domain,
                        siteInfo.sitename,
                    )
                    ndo.add_static_port_to_epg(
                        schema,
                        template.name,
                        bd.anp_name,
                        bd.epg.name,
                        siteInfo.sitename,
                        siteInfo.staticPorts,
                        strict_check=strictPortCheck,
                    )
                # update schema
                schema = ndo.save_schema(schema)
