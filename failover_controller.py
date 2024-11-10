import logging
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from ryu.topology import event, switches
from ryu.topology.api import get_link

class FailoverController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(FailoverController, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.datapaths = {}  # Armazena datapaths (switches) conectados
        self.link_status = {}  # Mantém o status dos links ativos
        self.logger.setLevel(logging.DEBUG)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        """Configuração inicial do switch ao conectar"""
        datapath = ev.msg.datapath
        self.datapaths[datapath.id] = datapath  # Guarda o switch
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # Instala regra padrão para enviar pacotes ao controlador
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        """Adiciona regras de fluxo ao switch"""
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                match=match, instructions=inst, buffer_id=buffer_id) if buffer_id else \
              parser.OFPFlowMod(datapath=datapath, priority=priority, match=match, instructions=inst)
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        # Filtra pacotes LLDP e IPv6 para simplificar
        if eth.ethertype == ether_types.ETH_TYPE_LLDP or eth.ethertype == ether_types.ETH_TYPE_IPV6:
            return

        dst = eth.dst
        src = eth.src
        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})

        # Registra porta do MAC de origem e registra como host
        self.mac_to_port[dpid][src] = in_port
        self.register_host(dpid, src, in_port)  # Adiciona este host à topologia

        # Redireciona para porta conhecida, ou envia para todas
        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [parser.OFPActionOutput(out_port)]
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst, eth_src=src)
            self.add_flow(datapath, 1, match, actions)

        # Envia pacote para porta apropriada
        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                in_port=in_port, actions=actions, data=msg.data)
        datapath.send_msg(out)

    def register_host(self, dpid, mac, port):
        """Registra o host na topologia do controlador"""
        self.logger.info(f"Host detectado: MAC {mac} no switch {dpid} na porta {port}")
        # Aqui, registre o host usando métodos apropriados para atualizar a topologia
    
    @set_ev_cls(event.EventLinkAdd, MAIN_DISPATCHER)
    @set_ev_cls(event.EventLinkDelete, MAIN_DISPATCHER)
    def link_event_handler(self, ev):
        """Gerencia eventos de adição e remoção de links"""
        link = ev.link
        src_dpid = link.src.dpid
        dst_dpid = link.dst.dpid
        src_port_no = link.src.port_no
        dst_port_no = link.dst.port_no

        # Verifica o tipo de evento e atualiza status
        if isinstance(ev, event.EventLinkAdd):
            self.link_status[(src_dpid, dst_dpid)] = True
            self.logger.info(f"Link ativo entre {src_dpid}:{src_port_no} -> {dst_dpid}:{dst_port_no}")
        elif isinstance(ev, event.EventLinkDelete):
            self.link_status[(src_dpid, dst_dpid)] = False
            self.logger.info(f"Link entre {src_dpid}:{src_port_no} -> {dst_dpid}:{dst_port_no} falhou")
            self.handle_failover(src_dpid, dst_dpid)

    def handle_failover(self, src_dpid, dst_dpid):
        """Lida com failover para rota alternativa"""
        self.logger.info(f"Falha detectada entre switches {src_dpid} e {dst_dpid}")
        alternative_links = self.get_alternative_links(src_dpid)

        for link in alternative_links:
            if self.link_status.get((link.src.dpid, link.dst.dpid), False):
                self.logger.info(f"Rota alternativa disponível entre {link.src.dpid} -> {link.dst.dpid}")
                # Configura regra de redirecionamento para failover
                self.add_failover_flow(link.src.dpid, link.dst.dpid)
                break

    def get_alternative_links(self, src_dpid):
        """Obtém links alternativos do switch de origem"""
        return [link for link in get_link(self) if link.src.dpid == src_dpid]

    def add_failover_flow(self, src_dpid, dst_dpid):
        """Configura regra de redirecionamento no switch"""
        datapath = self.datapaths.get(src_dpid)
        parser = datapath.ofproto_parser
        match = parser.OFPMatch()  # Ajuste conforme necessário
        actions = [parser.OFPActionOutput(dst_dpid)]
        self.add_flow(datapath, 1, match, actions)