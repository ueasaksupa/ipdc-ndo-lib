from ..core.configurations import *
from ..core.ndo_connector import NDOTemplate
from ..core.service_parameters import *


def create_service(
    ndo: NDOTemplate,
    srvParams: ServiceSimpleParameters,
    allowPushToUnSyncSchema: bool = True,
    strictPortCheck: bool = False,
):
    """
    For create service in NDO
    :param ndo: NDOTemplate instance
    :param srvParams: ServiceSimpleParameters instance
    """
    if not isinstance(srvParams, ServiceSimpleParameters):
        raise ValueError("srvParams must be instance of ServiceSimpleParameters class.")

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

    # ----- CREATE TEMPLATE ------
    for template in srvParams.templates:
        if template.name is not None:
            # prepare empty VRF template
            ndo.create_template(schema, template.name, tenant["id"])
            # associate site to template if template.associatedSites is all use allSiteList
            template_sites = allSiteList if template.associatedSites == "_all_" else template.associatedSites
            ndo.add_site_to_template(schema, template.name, template_sites)

        # ----- CREATE OBJECTS UNDER TEMPLATE ------
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

        if isinstance(template, EPGsTemplate):
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
