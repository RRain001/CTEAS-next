c-----------------------------------------------------------------------
      program p7o_oracle
c-----------------------------------------------------------------------
c
c --- CTEAS P7O FORTRAN ORACLE DRIVER -- hand written for this test
c     harness. This file is NOT vendor source and is never used by the
c     model; it drives the UNMODIFIED vendor unit and the generated
c     harnesses extracted by reference/p7o_source_anchor.py:
c       inject, p7o_cadence (verbatim POINTS1 release-cadence statements)
c       and p7o_release_state (verbatim POINTS1 release-time statements).
c
c --- Local names avoid every /PUFF/ symbol: IPUFCD, QM, QU, ZIMAX, ZIOLD
c     and V are common-block names, so a local with one of those names
c     would silently become an array read.
c
c --- Input on stdin, list directed:
c     line 1: mode
c     mode 1: icase nspec dt mfact0 heff hmax dpbl fmix istab mgauss q1 q2 q3
c             -> icase nspec ipufcd zimax ziold qm1 qu1 qm2 qu2 qm3 qu3
c     mode 2: icase wsnew xtmp1 mxnew dthr    -> icase npnew dt newpt1
c     mode 3: icase <vin(1..39)>              -> the /PUFF/ release fields
c
c --- <vin> is 39 values in this fixed order:
c     xpt1grd ypt1grd elstak sysrc szsrc heff xf bidsq fluxb fluxm
c     xfinb xfinm zfinb zfinm tipdw htstak exitw diam dt ws istab sqrts
c     iru tsigv tsigw el plx idw hb hw heff2 zly rinit xshift syini szini
c     j i itype
c-----------------------------------------------------------------------
      include 'params.puf'
      include 'puff.puf'
      include 'slug.puf'
c
      include 'flags.puf'
      integer mode,ios,icase,nspec_i,mfact0_i,istab_i,jj,mgauss_i
      real dt_i,heff_i,hmax_i,dpbl_i,fmix_i
      real qin(3),wsnew_i,xtmp1_i,dthr_i
      integer mxnew_i,npnew_o,newpt1_o
      real vin(39)
c
      read(*,*,iostat=ios) mode
      if(ios.ne.0) stop 'P7O oracle: missing mode'
c
      if(mode.eq.1)then
 10      read(*,*,iostat=ios) icase,nspec_i,dt_i,mfact0_i,heff_i,hmax_i,
     &                      dpbl_i,fmix_i,istab_i,mgauss_i,qin(1),
     &                      qin(2),qin(3)
         if(ios.ne.0) goto 999
         mgauss=mgauss_i
         do jj=1,3
            qm(jj,1)=0.0
            qu(jj,1)=0.0
         enddo
         call inject(1,nspec_i,dt_i,mfact0_i,qin,heff_i,hmax_i,dpbl_i,
     &               fmix_i,istab_i)
         write(*,'(i8,2(1x,i8),3(1x,es20.12),6(1x,es20.12))')
     &      icase,nspec_i,ipufcd(1),zimax(1),ziold(1),
     &      qm(1,1),qu(1,1),qm(2,1),qu(2,1),qm(3,1),qu(3,1)
         goto 10
      endif
c
      if(mode.eq.2)then
 20      read(*,*,iostat=ios) icase,wsnew_i,xtmp1_i,mxnew_i,dthr_i
         if(ios.ne.0) goto 999
         call p7o_cadence(wsnew_i,xtmp1_i,mxnew_i,dthr_i,npnew_o,
     &                    dt_i,newpt1_o)
         write(*,'(i8,2(1x,i8),1x,es20.12)') icase,npnew_o,newpt1_o,dt_i
         goto 20
      endif
c
 30   continue
      read(*,*,iostat=ios) icase,(vin(jj),jj=1,39)
      if(ios.ne.0) goto 999
      call p7o_release_state(vin)
      write(*,'(i8,46(1x,es20.12))') icase,
     &  xpb(1),ypb(1),zitibl(1),elbase(1),sigyb(1),sigzb(1),zfinal(1),
     &  zpb(1),zpe(1),xfinal(1),bidfnl(1),fb(1),fm(1),xbfin(1),xmfin(1),
     &  zbfin(1),zmfin(1),stipdw(1),FLOAT(isplit(1)),ht0(1),exitw0(1),
     &  diam0(1),temit0(1),ws0(1),FLOAT(istab0(1)),sqrts0(1),
     &  FLOAT(iru0(1)),sigv0(1),sigw0(1),el0(1),plexp0(1),srat0(1),
     &  FLOAT(idw0(1)),hb0(1),hw0(1),heff20(1),zly0(1),r0(1),xshift0(1),
     &  sysrc0(1),szsrc0(1),sy0(1),sz0(1),FLOAT(irlsnum(1)),
     &  FLOAT(isrcnum(1)),FLOAT(isrctyp(1))
      goto 30
c
 999  continue
      end
c-----------------------------------------------------------------------
      subroutine rolldn(np)
c-----------------------------------------------------------------------
c --- Stub for the array roll-down the cadence block may request when the
c     puff arrays are full; the parity cases keep them from filling.
      integer np
      write(*,*) 'P7O oracle: ROLLDN must not be called'
      stop 9
      end
