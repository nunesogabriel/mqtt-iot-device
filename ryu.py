from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_0
from ryu.lib.packet import packet, ethernet, ipv4, tcp, udp
from ryu.lib.packet import ether_types
from ryu.controller import dpset

class EnhancedSwitch(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_0.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(EnhancedSwitch, self).__init__(*args, **kwargs)
        self.mac_to_port = {}

    def add_flow(self, datapath, priority, match, actions):
        """Adiciona uma regra de fluxo ao switch com suporte para OpenFlow 1.0."""
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        mod = parser.OFPFlowMod(
            datapath=datapath, priority=priority,
            match=match, actions=actions)
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # Regra para redirecionar todo tráfego IP ao controlador
        match_ip = parser.OFPMatch(dl_type=ether_types.ETH_TYPE_IP)
        actions_controller = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER)]
        self.add_flow(datapath, 10, match_ip, actions_controller)

        self.logger.info("Regra para IP instalada no switch %s", datapath.id)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.in_port
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)

        # Loga informações básicas de MAC
        self.logger.info("Pacote recebido: MAC origem %s -> MAC destino %s, Porta de entrada: %s",
                         eth.src, eth.dst, in_port)

        # Verifica se é um pacote IPv4
        if eth.ethertype == ether_types.ETH_TYPE_IP:
            ipv4_pkt = pkt.get_protocol(ipv4.ipv4)
            self.logger.info("Pacote IPv4: %s -> %s", ipv4_pkt.src, ipv4_pkt.dst)
            
            # Identifica o protocolo (TCP ou UDP)
            if ipv4_pkt.proto == 6:  # TCP
                tcp_pkt = pkt.get_protocol(tcp.tcp)
                self.logger.info("Pacote TCP: %s -> %s, Porta destino: %d", ipv4_pkt.src, ipv4_pkt.dst, tcp_pkt.dst_port)
            elif ipv4_pkt.proto == 17:  # UDP
                udp_pkt = pkt.get_protocol(udp.udp)
                if udp_pkt.dst_port == 1883:
                    self.logger.info("Pacote MQTT UDP: %s -> %s, Porta destino: %d", ipv4_pkt.src, ipv4_pkt.dst, udp_pkt.dst_port)
                else:
                    self.logger.info("Pacote UDP: %s -> %s, Porta destino: %d", ipv4_pkt.src, ipv4_pkt.dst, udp_pkt.dst_port)
        else:
            self.logger.info("Pacote não-IP recebido: Tipo de Ethernet %s", eth.ethertype)

        # Aprendizado de endereço MAC e encaminhamento simples
        self.mac_to_port[datapath.id] = self.mac_to_port.get(datapath.id, {})
        self.mac_to_port[datapath.id][eth.src] = in_port

        # Encontra a porta de destino e realiza o encaminhamento ou flooding
        if eth.dst in self.mac_to_port[datapath.id]:
            out_port = self.mac_to_port[datapath.id][eth.dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [parser.OFPActionOutput(out_port)]
        match = parser.OFPMatch(in_port=in_port, dl_dst=eth.dst, dl_src=eth.src)
        self.add_flow(datapath, 1, match, actions)

        # Envia o pacote pela porta apropriada
        out = parser.OFPPacketOut(
            datapath=datapath, buffer_id=msg.buffer_id, in_port=in_port,
            actions=actions, data=msg.data)
        datapath.send_msg(out)